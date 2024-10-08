#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ====================
#       Set-up
# ====================

# Import required modules
import html
import re
import unicodedata
from buzzmain.Marc.marc8_to_unicode import marc8_to_unicode
from buzzmain.Marc.marc_validation import *

__author__ = 'Victoria Morris'
__license__ = 'MIT License'
__version__ = '1.0.0'
__status__ = '4 - Beta Development'


# ====================
#     Constants
# ====================

LEADER_LENGTH, DIRECTORY_ENTRY_LENGTH = 24, 12
SUBFIELD_MARKER, END_OF_FIELD, END_OF_RECORD = chr(0x1F), chr(0x1E), chr(0x1D)
ALEPH_CONTROL_FIELDS = ['DB ', 'DB', 'SYS', 'FMT', 'SYSID']
FIELDS_TO_IGNORE = ['CAT', 'LAS']

# ====================
#     Exceptions
# ====================


class RecordLengthError(Exception):
    def __str__(self): return 'Invalid record length in first 5 bytes of record'


class LeaderError(Exception):
    def __str__(self): return 'Error reading record leader'


class DirectoryError(Exception):
    def __str__(self): return 'Record directory is invalid'


class FieldsError(Exception):
    def __str__(self): return 'Error locating fields in record'


class BaseAddressLengthError(Exception):
    def __str__(self): return 'Base address exceeds size of record'


class BaseAddressError(Exception):
    def __str__(self): return 'Error locating base address of record'


class WriteNeedsRecord(Exception):
    def __str__(self): return "Write requires a Record object as an argument"


class FieldNotFound(Exception):
    def __str__(self): return "Field not found"


# ====================
#       Classes
# ====================


class MARCReader(object):

    def __init__(self, marc_target):
        if hasattr(marc_target, 'read') and callable(marc_target.read):
            self.file_handle = marc_target

    def __iter__(self):
        return self

    def close(self):
        if self.file_handle:
            self.file_handle.close()

    def __next__(self):
        first5 = self.file_handle.read(5)
        if not first5: raise StopIteration
        if len(first5) < 5: raise RecordLengthError
        return Record(first5 + self.file_handle.read(int(first5) - 5))


class MARCWriter(object):

    def __init__(self, marc_target) -> None:
        if hasattr(marc_target, 'read') and callable(marc_target.read):
            self.file_handle = marc_target

    def write(self, record) -> None:
        if not isinstance(record, Record):
            raise WriteNeedsRecord
        self.file_handle.write(record.as_marc())

    def flush(self) -> None:
        self.file_handle.flush()

    def close(self) -> None:
        self.file_handle.close()


class Record(object):
    def __init__(self, data='', leader=' ' * LEADER_LENGTH, marc8=False):
        self.leader = '{}22{}4500'.format(leader[0:10], leader[12:20])
        self.fields = list()
        self.pos = 0
        self.marc8 = marc8
        self.errors = None
        self.originalFormat = 'MARC'
        if len(data) > 0:
            self.decode_marc(data)

    def from_string(self, data):
        for field in data.split('\n'):
            field = field.strip()
            tag = field.split(' ', 1)[0].strip('=')
            if tag == 'LDR':
                self.leader = field[6:].replace('#', ' ').replace('^', ' ')
            elif tag in ALEPH_CONTROL_FIELDS:
                continue
            elif len(field) > 3:
                self.add_field_from_string(field)

    def from_MRC_string(self, data):
        self.originalFormat = 'Aleph'
        for field in data.split('\n'):
            field = field.strip()
            tag = field.split(' ', 1)[0].strip()
            if tag == 'LDR':
                self.leader = field[8:].replace('#', ' ').replace('^', ' ')
            elif tag in ALEPH_CONTROL_FIELDS:
                continue
            elif len(field) > 3:
                self.add_field_from_MRC_string(field)
        return self

    def __getitem__(self, tag):
        fields = self.get_fields(tag)
        if len(fields) > 0: return fields[0]
        return None

    def __contains__(self, tag):
        fields = self.get_fields(tag)
        return len(fields) > 0

    def __iter__(self):
        self.__pos = 0
        return self

    def __next__(self):
        if self.__pos >= len(self.fields): raise StopIteration
        self.__pos += 1
        return self.fields[self.__pos - 1]

    def __str__(self):
        text_list = ['=LDR  {}'.format(self.leader)]
        text_list.extend([str(field) for field in self.fields])
        return '\n'.join(text_list) + '\n'

    def get_fields(self, *args):
        if len(args) == 0: return self.fields
        flds = [f for f in self.fields if f.tag in args]
        if 'LDR' in args:
            flds.append(self.leader)
        return flds

    def add_field(self, *fields):
        for fld in fields:
            if len(self.fields) == 0 or not fld.tag.isdigit():
                self.fields.append(fld)
                continue
            self._sort_fields(fld)

    def remove_field(self, *fields):
        for f in fields:
            try:
                self.fields.remove(f)
            except ValueError:
                raise FieldNotFound

    def _sort_fields(self, field):
        tag = int(field.tag)
        i, last_tag = 0, 0
        for selff in self.fields:
            i += 1
            if not selff.tag.isdigit():
                self.fields.insert(i - 1, field)
                break

            last_tag = int(selff.tag)

            if last_tag > tag:
                self.fields.insert(i - 1, field)
                break
            if len(self.fields) == i:
                self.fields.append(field)
                break

    def decode_marc(self, marc):
        # Extract record leader
        try:
            self.leader = marc[0:LEADER_LENGTH].decode('ascii')
        except:
            print('Record has problem with Leader and cannot be processed')
        if len(self.leader) != LEADER_LENGTH: raise LeaderError

        # Extract the byte offset where the record data starts
        base_address = int(marc[12:17])
        if base_address <= 0: raise BaseAddressError
        if base_address >= len(marc): raise BaseAddressLengthError

        # Extract directory
        # base_address-1 is used since the directory ends with an END_OF_FIELD byte
        directory = marc[LEADER_LENGTH:base_address - 1].decode('ascii')

        field_tags = [directory[i:i+10] for i in range(0, len(directory), 12) ]
        field_data = marc[base_address:-2].split(b'\x1e')
        if len(field_tags) != len(field_data):
            print(f'Number of field tags {str(len(field_tags))} does not match number of fields {str(len(field_data))}')
            print(str(field_tags))
            print(str(field_data))
        fields_list = dict(zip(field_tags, field_data))
        field_count = 0
        for tag_key in fields_list:
            tag = tag_key[:3]
            if str(tag) < '010' and tag.isdigit():
                field = Field(tag=tag, data=fields_list[tag_key].decode('utf-8'))
            elif str(tag) in ALEPH_CONTROL_FIELDS:
                continue
            else:
                subfields = list()
                subs = fields_list[tag_key].split(b'\x1f')
                try: subs[0] = subs[0].decode('ascii') + '  '
                except: subs[0] = '   '
                first_indicator, second_indicator = subs[0][0], subs[0][1]

                for subfield in subs[1:]:
                    if len(subfield) == 0: continue

                    try:
                        code, data = subfield[0:1].decode('ascii'), subfield[1:].decode('utf-8', 'strict')
                    except:
                        print('Error in subfield code')
                    else:
                        if self.marc8:
                            data = marc8_to_unicode(data)
                        subfields.append(code)
                        subfields.append(html.unescape(data))
                field = Field(tag=tag, indicators=[first_indicator, second_indicator], subfields=subfields)
            self.add_field(field)
            field_count += 1

        if field_count == 0:
            print('fields error')
            raise FieldsError

    def as_marc(self):
        fields, directory = b'', b''
        offset = 0

        for field in self.fields:
            field_data = field.as_marc()
            fields += field_data
            if field.tag.isdigit():
                directory += ('%03d' % int(field.tag)).encode('utf-8')
            else:
                directory += ('%03s' % field.tag).encode('utf-8')
            directory += ('%04d%05d' % (len(field_data), offset)).encode('utf-8')
            offset += len(field_data)

        directory += END_OF_FIELD.encode('utf-8')
        fields += END_OF_RECORD.encode('utf-8')
        base_address = LEADER_LENGTH + len(directory)
        record_length = base_address + len(fields)
        strleader = '%05d%s%05d%s' % (record_length, self.leader[5:12], base_address, self.leader[17:])
        leader = strleader.encode('utf-8')
        return leader + directory + fields

    def validate(self):

        self.errors = {
            'structure': set(),
            'completeness': set(),
            'obsolete coding': set(),
            'abbreviations': set(),
            }

        for field_tag in CONTROL_FIELDS:
            status, err = CONTROL_FIELDS[field_tag].check_cardinality(self)
            if not status:
                self.errors['structure'].add(f'{field_tag}|Serious|{err}')
        for field_tag in DATA_FIELDS:
            status, err = DATA_FIELDS[field_tag].check_cardinality(self)
            if not status:
                self.errors['structure'].add(f'{field_tag}|Serious|{err}')

        for field in self.fields:
            f_errors = field.validate()
            for error_type in f_errors:
                if f_errors[error_type]:
                    for err in f_errors[error_type]:
                        self.errors[error_type].add(f'{field.tag}|Serious|{err}')
            if field.tag in OBSOLETE_FIELDS:
                self.errors['obsolete coding'].add(f'{field.tag}|Serious|Field is obsolete.')
            if field.tag in UNDESIRABLE_FIELDS:
                self.errors['obsolete coding'].add(f'{field.tag}|Moderate|{UNDESIRABLE_FIELDS[field.tag]}')

        '''
        for field_tag in DESIRABLE_FIELDS:
            if field_tag == '1xx':
                find = self.get_fields('100', '110', '111', '130')
            else:
                find = self.get_fields(field_tag)
            if len(find) < 1:
                self.errors['completeness'].append(f'{field_tag}|Moderate|Desirable field not found.')
        for abb in ABBREVIATIONS:
            for field in self:
                for subfield in field:
                    if abb.search(subfield[1]):
                        m = abb.search(subfield[1]).group(0)
                        self.errors['abbreviations'].append(f'{field.tag}|Ignorable|Abbreviation <span class="fw-bolder">{str(m)}</span> in subfield {subfield[0]} - expand to <span class="fw-bolder">{ABBREVIATIONS[abb]}</span>?')
        '''
        num_errors = sum(len(self.errors[e]) for e in self.errors)
        if num_errors == 0:
            return True, None
        return False, self.errors

    def add_field_from_string(self, text_input=''):
        """Accepts fields of the form '=035  ## $a(OCoLC)556544347'"""
        if '$' in text_input:
            subfields = []
            for s in text_input[10:].split('$'):
                try:
                    subfields.extend([s[0], s[1:]])
                except:
                    continue
            self.add_field(Field(tag=text_input[1:4], indicators=[text_input[6].replace('#', ' '), text_input[7].replace('#', ' ')], subfields=subfields))
        else:
            self.add_field(Field(tag=text_input[1:4], data=text_input[6:].replace('#', ' ')))

    def add_field_from_MRC_string(self, text_input=''):
        """Accepts fields of the form '300   L $$axvi, 239 pages ;$$c(12º)'"""
        if '$$' in text_input:
            subfields = []
            for s in text_input[10:].split('$$'):
                subfields.extend([s[0], s[1:]])
            self.add_field(Field(tag=text_input[0:3], indicators=[text_input[3], text_input[4]], subfields=subfields))
        else:
            self.add_field(Field(tag=text_input[0:3], data=text_input[8:].replace('^', ' ')))


class Field(object):

    def __init__(self, tag, indicators=None, subfields=None, data=''):
        if indicators is None: indicators = []
        if subfields is None: subfields = []
        indicators = [str(x) for x in indicators]

        # Normalize tag to three digits
        self.tag = '%03s' % tag

        # Check if tag is a control field
        if self.tag < '010' and self.tag.isdigit():
            self.data = str(data)
        elif self.tag in ALEPH_CONTROL_FIELDS:
            self.data = str(data)
        else:
            self.indicators = indicators
            while len(self.indicators) < 2:
                self.indicators.append(' ')
            if len(self.indicators) > 2:
                self.indicators = self.indicators[:2]
            if self.indicators[0] in ['#', '.', '^', '\u001F', '\u001E', '\u001C']:
                self.indicators[0] = ' '
            if self.indicators[1] in ['#', '.', '^', '\u001F', '\u001E', '\u001C']:
                self.indicators[1] = ' '
            self.subfields = subfields
        self.errors = None

    def __iter__(self):
        self.__pos = 0
        return self

    def __getitem__(self, subfield):
        subfields = self.get_subfields(subfield)
        if len(subfields) > 0: return subfields[0]
        return None

    def __contains__(self, subfield):
        subfields = self.get_subfields(subfield)
        return len(subfields) > 0

    def __next__(self):
        if not hasattr(self, 'subfields'):
            raise StopIteration
        while self.__pos + 1 < len(self.subfields):
            subfield = (self.subfields[self.__pos], self.subfields[self.__pos + 1])
            self.__pos += 2
            return subfield
        raise StopIteration

    def __str__(self):
        if self.is_control_field() or self.tag in ALEPH_CONTROL_FIELDS:
            return '={}  {}'.format(self.tag, self.data.replace(' ', '#'))
        text = '={}  '.format(self.tag)
        for indicator in self.indicators:
            if indicator in [' ', '#', '.', '^']:
                text += '#'
            else:
                text += indicator
        text += ' '
        for subfield in self:
            text += '${}{}'.format(subfield[0], subfield[1])
        return text

    def text(self, subfields=''):
        if self.is_control_field() or self.tag in ALEPH_CONTROL_FIELDS:
            return self.data.replace(' ', '#')
        if not subfields:
            return ' '.join(subfield[1] for subfield in self)
        return ' '.join(subfield[1] for subfield in self if subfield[0] in subfields)

    def get_subfields(self, *codes):
        values = []
        for subfield in self:
            if len(codes) == 0 or subfield[0] in codes:
                values.append(str(subfield[1]))
        return values

    def is_control_field(self):
        if self.tag < '010' and self.tag.isdigit(): return True
        if self.tag in ALEPH_CONTROL_FIELDS: return True
        return False

    def as_marc(self):
        if self.is_control_field():
            return (self.data + END_OF_FIELD).encode('utf-8')
        marc = self.indicators[0] + self.indicators[1]
        for subfield in self:
            marc += SUBFIELD_MARKER + subfield[0] + subfield[1]
        return (marc + END_OF_FIELD).encode('utf-8')

    def validate(self):
        self.errors = {
            'structure': set(),
            'completeness': set(),
            'obsolete coding': set(),
            'abbreviations': set(),
        }
        if self.tag in CONTROL_FIELDS:
            test, message = CONTROL_FIELDS[self.tag].check_content(self)
            if not test:
                self.errors['structure'].add(message)
        elif self.tag in DATA_FIELDS:
            test, messages = DATA_FIELDS[self.tag].check_indicators(self)
            if not test:
                self.errors['structure'].update(messages)
            test, messages = DATA_FIELDS[self.tag].check_subfields(self)
            if not test:
                self.errors['structure'].update(messages)
        else:
            self.errors['structure'].add('Field is not valid')
        return self.errors
