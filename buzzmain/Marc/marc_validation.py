#!/usr/bin/env python
# -*- coding: utf-8 -*-
import regex as re

CARDINALITIES = {
    '?': 'Optional; not repeatable',
    '1': 'Mandatory; not repeatable',
    '*': 'Optional; repeatable',
    '+': 'Mandatory; repeatable'
}

OBSOLETE_FIELDS = ['009', '011', '039', '090', '090', '091', '211', '212', '214', '241', '265',
                   '301', '302', '303', '304', '305', '308', '315', '350', '359',
                   '440', '503', '512', '517', '523', '527', '537', '543', '570', '582', '590', ' 597', '599',
                   '652', '692', '705', '715', '755', '840', '851', '870', '871', '872', '873',
                   '917', '958', '962', '963', '964', '975', '976', '980', '992']
UNDESIRABLE_FIELDS = {'260': 'Prefer field 264',
                      '720': 'Prefer a controlled field in the 7xx block',
                      '653': 'Prefer a controlled subject term in the 6xx block'}

DESIRABLE_FIELDS = ['1xx', '264', '300', '336', '337', '338']

ABBREVIATIONS = {
    re.compile(r'\bpp*\b\.?'): 'pages',
    re.compile(r'\bsh\b\.?'): 'sheet(s)',
    re.compile(r'\billu?s?\b\.?'): 'illustrations',
    re.compile(r'\bfacsi?m?s?\b\.?'): 'facsimiles',
    re.compile(r'\bgeneal\b\.?'): 'genealogical',
    re.compile(r'\bports?\b\.?'): 'portraits',
    re.compile(r'\bcol\b\.?'): 'colour or column(s)',
    re.compile(r'\bmins?\b\.?'): 'minute(s) or miniature',
}


class GenericField:

    def __init__(self, tag, cardinality):
        self.tag = tag
        if cardinality not in CARDINALITIES:
            raise f'Invalid cardinality {str(cardinality)} for field {tag}'
        self.cardinality = cardinality

    def check_cardinality(self, rec):
        count = len(rec.get_fields(self.tag))
        if self.cardinality == '?':
            if count > 1:
                return False, f'Field is not repeatable, but occurs {str(count)} times'
            return True, ''
        if self.cardinality == '1':
            if count == 0:
                return False, f'Field is not present, but should occur exactly once'
            if count != 1:
                return False, f'Field should occur exactly once, but occurs {str(count)} times'
            return True, ''
        if self.cardinality == '*':
            return True, ''
        if self.cardinality == '+':
            if count == 0:
                return False, f'Field is not present, but should occur at least once'
            if count < 1:
                return False, f'Field should occur at least once, but occurs {str(count)} times'
            return True, ''
        raise f'Invalid cardinality {str(self.cardinality)} for field {self.tag}'


class DataField(GenericField):

    def __init__(self, tag, cardinality, indicators, subfields):
        super().__init__(tag, cardinality)
        self.indicators = indicators
        self.subfields = re.compile(subfields)

    def check_indicators(self, field):
        test = True
        messages = []
        i1 = self.indicators[0].replace(' ', '#')
        i2 = self.indicators[1].replace(' ', '#')
        check1 = field.indicators[0].replace(" ", "#")
        check2 = field.indicators[1].replace(" ", "#")
        if check1 not in i1:
            messages.append(f'Incorrect 1st indicator: {check1} '
                            f'should be {"one of: " if len(i1) > 1 else ""}'
                            f'{i1}')
            test = False
        if check2 not in i2:
            messages.append(f'Incorrect 2nd indicator: {check2} '
                            f'should be {"one of: " if len(i2) > 1 else ""}'
                            f'{i2}')
            test = False
        return test, messages

    def check_subfields(self, field):
        test = True
        messages = []
        subfield_codes = ''.join(subfield[0] for subfield in field)
        if not self.subfields.match(subfield_codes):
            allowable = re.sub(r'[^a-z0-9]', '', self.subfields.pattern)
            for code in set(subfield[0] for subfield in field):
                if code not in allowable:
                    messages.append(f'Subfield {code} is not valid for this field')
            test = False
            if field.tag in SUBFIELDS:
                for t in SUBFIELDS[field.tag]:
                    t_test, t_messages = SUBFIELDS[field.tag][t].check_cardinality(field)
                    if not t_test:
                        messages.append(t_messages)
                    t_test, t_messages = SUBFIELDS[field.tag][t].check_order(field)
                    if not t_test:
                        messages.extend(t_messages)
        return test, messages


class ControlField(GenericField):

    def __init__(self, tag, cardinality, regex):
        super().__init__(tag, cardinality)
        self.regex = re.compile(regex)

    def check_content(self, field):
        if not self.regex.match(field.data):
            return False, f'Incorrect content: \'{str(field.data)}\' should follow pattern \'{self.regex.pattern}\''
        return True, ''


def mid(s):
    s = s.replace("^", "").replace("$", "")
    if len(s) > 1:
        return 'one of these subfields:'
    return 'subfield'


class Subfield:

    def __init__(self, tag, cardinality, before, after):
        self.tag, self.code = tag.split('$')
        if cardinality not in CARDINALITIES:
            raise f'Invalid cardinality {str(cardinality)} for field {self.tag} subfield {self.code}'
        self.cardinality = str(cardinality)
        self.before = before
        self.after = after

    def __str__(self):
        return f'Field {self.tag}, subfield {self.code}\n' \
               f'\t{CARDINALITIES[self.cardinality]}\n' \
               f'\t{self.before_string()}\n\t{self.after_string()}'

    def before_string(self):
        if self.before == '^':
            return 'Should be the first subfield in the field'
        if '^' in self.before:
            return (f'Should occur either at the start of the field, '
                    f'or after {mid(self.before)} {self.before.replace("^", "")}')
        return f'Should follow {mid(self.before)} {self.before}'

    def after_string(self):
        if self.after == '$':
            return 'Should be the last subfield in the field'
        if '$' in self.after:
            return (f'Should occur either at the end of the field, '
                    f'or before {mid(self.after)} {self.after.replace("$", "")}')
        return f'Should occur before {mid(self.after)} {self.after}'

    def check_cardinality(self, field):
        if field.tag != self.tag:
            raise f'Attempted to check {field.tag} against {self.tag} subfield {self.code}'
        count = len(field.get_subfields(self.code))
        if self.cardinality == '?':
            if count > 1:
                return False, f'Subfield {self.code} is not repeatable, but occurs {str(count)} times'
            return True, ''
        if self.cardinality == '1':
            if count == 0:
                return False, f'Subfield {self.code} is not present, but should occur exactly once'
            if count != 1:
                return False, f'Subfield {self.code} should occur exactly once, but occurs {str(count)} times'
            return True, ''
        if self.cardinality == '*':
            return True, ''
        if self.cardinality == '+':
            if count == 0:
                return False, f'Subfield {self.code} is not present, but should occur at least once'
            if count < 1:
                return False, f'Subfield {self.code} should occur at least once, but occurs {str(count)} times'
            return True, ''
        raise f'Invalid cardinality {str(self.cardinality)} for field {self.tag} subfield {self.code}'

    def check_order(self, field):
        test = True
        messages = []
        subfield_codes = ['^', ] + [subfield[0] for subfield in field] + ['$', ]
        if self.code not in subfield_codes:
            return False, ''
        for i, code in enumerate(subfield_codes):
            if code != self.code:
                continue
            before = subfield_codes[i - 1]
            if before not in self.before:
                test = False
                messages.append(f'Subfield {self.code} {self.before_string().lower()}')
            after = subfield_codes[i + 1]
            if after not in self.after:
                test = False
                messages.append(f'Subfield {self.code} {self.after_string().lower()}')
        return test, messages


CONTROL_FIELDS = {
    '001': ['1', '^[0-9]{9}$'],
    '003': ['1', '^Uk$'],
    '005': ['1', '^.*$'],
    '006': ['*', '^.*$'],
    '007': ['*', '^.*$'],
    '008': ['1', '^.*$'],
    'WII': ['*', '^(ESTAR[12]|ETOC|ld:journal|ld:ebook|WW1|GOOGLEBOOKS|PLAYBILL|DCW|MSD|DISCOVERY)$'],
}

for field_tag in CONTROL_FIELDS:
    CONTROL_FIELDS[field_tag] = ControlField(field_tag, *CONTROL_FIELDS[field_tag])

DATA_FIELDS = {
    '010': ['?', [' ', ' '], '^8*(a(b*|z*)|b+|z+)$'],  # Library of Congress Control Number
    '011': ['*', [' ', ' '], '^a+$'],  # Linking Library of Congress Control Number
    '013': ['*', [' ', ' '], '^8*6?ab?c?(de?)*f*$'],  # Patent Control Information
    '015': ['*', [' ', ' '], '^8*6?(a+|z)z*q*2?$'],  # National Bibliography Number
    '016': ['*', [' 7', ' '], '^8*[az]z*2?$'],  # National Bibliographic Agency Control Number
    '017': ['*', [' ', ' 8'], '8*6?i?(a+|z)z*bd?2?$'],  # Copyright or Legal Deposit Number
    '018': ['?', [' ', ' '], '^8*6?a$'],  # Copyright Article-Fee Code
    '019': ['*', ['0123456789acdegmnoprstuxy', ' '], '^a$'],  # Legacy Control Number
    '020': ['*', [' ', ' '], '^8*6?(a+|z)z*q*c?$'],  # International Standard Book Number
    '022': ['*', [' 01', ' '], '^8*6?(((al?|l)m*|(m+|y))y*|z)z*2?0?1*$'],  # International Standard Serial Number
    '023': ['*', ['01', ' '], '^8*6?(a+2?|y|z)y*z*0?1*$'],  # Cluster ISSN
    '024': ['*', ['0123478', ' 01'], '^8*6?(ad?|zd?)(zd?)*q*c?2?$'],  # Other Standard Identifier
    '025': ['*', [' ', ' '], '^8*a+$'],  # Overseas Acquisition Number
    '026': ['*', [' ', ' '], '^8*6?(abc?d*|e)2?5*$'],  # Fingerprint Identifier
    '027': ['*', [' ', ' '], '^8*6?[az]z*q*$'],  # Standard Technical Report Number
    '028': ['*', ['0123456', '0123'], '^8*6?abq*$'],  # Publisher or Distributor Number
    '030': ['*', [' ', ' '], '^8*6?[az]z*$'],  # CODEN Designation
    '031': ['*', [' ', ' '], '^8*6?abcm?e?d*t*r?g?n?o?t*p?u*q*s*y*z*2?$'],  # Musical Incipits Information
    '032': ['*', [' ', ' '], '^8*6?ab$'],  # Postal Registration Number
    '033': ['*', [' 012', ' 012'], '^8*6?3?(a|(bc?)|p)+0*1*2?$'],  # Date/Time and Place of an Event
    '034': ['*', ['013', ' 01'], '^8*6?3?a(b*c*(defg)?|h(ikmn)?p?)r?s*t*x?y?z?0*1*2?$'],
    # Coded Cartographic Mathematical Data
    '035': ['*', [' ', ' '], '^8*6?[az]z*$'],  # System Control Number
    '036': ['?', [' ', ' '], '^8*6?ab$'],  # Original Study Number for Computer Data files
    '037': ['*', [' 23', ' '], '^3?a?bn*5?$'],  # Source of Acquisition
    '038': ['?', [' ', ' '], '^8*6?a$'],  # Record Content Licensor
    '039': ['?', ['12', ' '], '^p?a$'],  # National Bibliography Issue Number
    '040': ['1', [' ', ' '], '^8*6?abc?d*e*$'],  # Cataloging Source
    '041': ['*', [' 01', ' 7'], '^8*6?3?a+b*d*e*f*g*h*i*j*k*m*n*p*q*r*t*2?7*$'],  # Language Code
    '042': ['?', [' ', ' '], '^a+$'],  # Authentication Code
    '043': ['*', [' ', ' '], '^8*6?(a+b*c*|b+c*|c+)0*1*2?$'],  # Geographic Area Code
    '044': ['?', [' ', ' '], '^8*6?(a+b*c*|b+c*|c+)2?$'],  # Country of Publishing/Producing Entity Code
    '045': ['?', [' 012', ' '], '^8*6?a*(c+b*|c*b+)$'],  # Time Period of Content
    '046': ['*', [' 123', ' '], '^8*6?3?a[bckmo][delnp]x*z*2?$'],  # Special Coded Dates
    '047': ['*', [' ', ' 7'], '^8*a+2?$'],  # Form of Musical Composition Code
    '048': ['*', [' ', ' 7'], '^8*[ab]+2?$'],  # Number of Musical Instruments or Voices Code
    '050': ['*', [' 01', '04'], '^8*6?3?a+b?0?1?$'],  # Library of Congress Call Number
    '051': ['*', [' ', ' '], '^8*ab?c?$'],  # Library of Congress Copy, Issue, Offprint Statement
    '052': ['*', [' 17', ' '], '^8*6?ab*d*0?1?2?$'],  # Geographic Classification
    '055': ['*', [' 01', '0123456789'], '^8*6?ab?0?1?2?$'],  # Classification Numbers Assigned in Canada
    '060': ['*', [' 01', '04'], '^8*a+b?0?1?$'],  # National Library of Medicine Call Number
    '061': ['*', [' ', ' '], '^8*a+b?c?$'],  # National Library of Medicine Copy Statement
    '066': ['?', [' ', ' '], '^[abc]c*$'],  # Character Sets Present
    '070': ['*', [' 01', ' '], '^8*a+b?0?1?$'],  # National Agricultural Library Call Number
    '071': ['*', [' ', ' '], '^8*a+b?c*$'],  # National Agricultural Library Copy Statement
    '072': ['*', [' ', '07'], '^8*6?ax*2?$'],  # Subject Category Code
    '074': ['*', [' ', ' '], '^8*[az]z*$'],  # GPO Item Number
    '080': ['*', [' 01', ' '], '^8*6?ab?x*0?1?2?$'],  # Universal Decimal Classification Number
    '082': ['*', ['017', ' 04'], '^8*6?a+b?2?m?q?7*$'],  # Dewey Decimal Classification Number
    '083': ['*', ['017', ' '], '^8*6?(az?y?)+c*m?2?q?7*$'],  # Additional Dewey Decimal Classification Number
    '084': ['*', [' ', ' '], '^8*6?a+b?2?q?0?1?7*$'],  # Other Classification Number
    '085': ['*', [' ', ' '], '^8*6?k0?1?$'],  # Synthesized Classification Number Components
    '086': ['*', [' 01', ' '], '^8*6?[az]z*2?0?1?$'],  # Government Document Classification Number
    '088': ['*', [' ', ' '], '^8*6?[az]z*$'],  # Report Number
    '090': ['*', [' ', ' '], '^ab?$'],  # Local Call Number
    '091': ['?', [' ', ' '], '^a$'],  # Previous Control Number (Document Supply Conference)
    '100': ['?', ['013', ' '], '^8*6?ab?q?c?q?d?c?j*u?t?[np]*[lf]*k?[lf]*e*4*0?1?2?7*$'],  # Main Entry-Personal Name
    '110': ['?', ['012', ' '], '^8*6?ab*u?t?[np]*d?c?[np]*g*[lf]*k?[lf]*[np]*e*4*0?1?2?7*$'],
    # Main Entry-Corporate Name
    '111': ['?', ['012', ' '], '^8*6?aq?e*u?t?[np]*d?c?[np]*g*[lk]*f?[lk]*[np]*e*j*4*0?1?2?7*$'],
    # Main Entry-Meeting Name
    '130': ['?', ['0123456789', ' '], '^8*6?a[np]*d*m*[np]*o?r?g*k*l?s*g*k*f?k*s*d*[np]*0?1?2?7*$'],
    # Main Entry-Uniform Title
    '210': ['*', ['01', ' 0'], '^8*6?ab??2?7*$'],  # Abbreviated Title
    '211': ['*', ['01', '0123456789'], '^6?a$'],  # Acronym Or Shortened Title
    '212': ['*', ['01', ' '], '^6?a$'],  # Variant Access Title
    '214': ['*', ['01', '0123456789'], '^6?a$'],  # Augmented Title
    '222': ['*', [' ', '0123456789'], '^8*6?ab?$'],  # Key Title
    '240': ['?', ['01', '0123456789'], '^8*6?a[np]*h?d*m*[np]*o?r?g*k*l?s*g*k*f?k*s*d*[np]*2?0?1?7*$'],  # Uniform Title
    '241': ['?', ['01', '0123456789'], '^ah?$'],  # Romanized Title
    '242': ['*', ['01', '0123456789'], '^8*6?a[np]*h?b?[np]*c?y?$'],  # Translation of Title by Cataloging Agency
    '243': ['?', ['01', '0123456789'], '^8*6?a[np]*h?d*m*[np]*o?r?g*k*l?s*g*k*f?k*s*d*[np]*$'],
    # Collective Uniform Title
    '245': ['1', ['01', '0123456789'], '^8*6?(a[np]*h?b?[np]*|k)k*f?g?k*[np]*s?c?7*$'],  # Title Statement
    '246': ['*', ['0123', ' 012345678'], '^8*6?i*a[np]*h?b?[np]*f?g*[np]*5?7*$'],  # Varying Form of Title
    '247': ['*', ['01', '01'], '^8*6?a[np]*h?b?[np]*f?g*[np]*x?7*$'],  # Former Title
    '250': ['*', [' ', ' '], '^8*6?3?ab?7*$'],  # Edition Statement
    '251': ['*', [' ', ' '], '^8*6?3?a+?2?0?1?$'],  # Version Information
    '254': ['?', [' ', ' '], '^8*6?a$'],  # Musical Presentation Statement
    '255': ['*', [' ', ' '], '^8*6?ab?([cd]?e?|f?g?)7*$'],  # Cartographic Mathematical Data
    '256': ['?', [' ', ' '], '^8*6?a7*$'],  # Computer File Characteristics
    '257': ['*', [' ', ' '], '^8*6?a+2?0?1?$'],  # Country of Producing Entity
    '258': ['*', [' ', ' '], '^8*6?ab?$'],  # Philatelic Issue Data
    '260': ['*', [' 23', ' '], '^8*6?3?(a+b+c*)+((ef)*g*)*$'],  # Publication, Distribution, etc. (Imprint)
    '261': ['?', [' ', ' '], '^8*6?(?=[abe])a*b*d*e*f*$'],  # Imprint Statement For Films
    '262': ['?', [' ', ' '], '^8*6?(?=[abc])a?b?c?k?l?$'],  # Imprint Statement For Sound Recordings
    '263': ['?', [' ', ' '], '^8*6?a$'],  # Projected Publication Date
    '264': ['*', [' 23', '01234'], '^8*6?3?(a+b+c*)+7*$'],
    # Production, Publication, Distribution, Manufacture, and Copyright Notice
    '265': ['?', [' ', ' '], '^6?a+$'],  # Source For Acquisition/Subscription Address
    '270': ['*', [' 12', ' 07'], '^8*6?i?f?g?h?(a+b?c?d?e?j*k*l*m*n*|j+k*l*m*n*|k+l*m*n*|l+m*n*|m+n*|n+)p*q*r*z*4*$'],
    # Address
    '300': ['*', [' ', ' '], '^8*6?3?a+b?c*e?(a*f*g*)*7*$'],  # Physical Description
    '301': ['*', [' ', ' '], '^ab?c?d?e?f?$'],  # Physical Description For Films
    '302': ['*', [' ', ' '], '^a$'],  # Page Or Item Count
    '303': ['*', [' ', ' '], '^a$'],  # Unit Count
    '304': ['*', [' ', ' '], '^a$'],  # Linear Footage
    '305': ['*', [' ', ' '], '^6?ab?c?d?e?f?m?n?$'],  # Physical Description For Sound Recordings
    '306': ['?', [' ', ' '], '^8*6?a+$'],  # Playing Time
    '307': ['*', [' 8', ' '], '^8*6?ab?$'],  # Hours, Etc.
    '308': ['*', [' ', ' '], '^6?ab?c?d?e?f?$'],  # Physical Description For Films (Archival)
    '310': ['*', [' ', ' '], '^8*6?ab?2?0?1?$'],  # Current Publication Frequency
    '315': ['?', [' ', ' '], '^6?a+b*$'],  # Frequency
    '321': ['*', [' ', ' '], '^8*6?ab?2?0?1?$'],  # Former Publication Frequency
    '334': ['*', [' ', ' '], '^8*6?(ab?|b)2?0?1?$'],  # Mode of Issuance
    '335': ['*', [' ', ' '], '^8*6?3?(ab?|b)2?0?1?7*$'],  # Extension Plan
    '336': ['*', [' ', ' '], '^8*6?3?a*[ab]b*2?0?1?7*$'],  # Content Type
    '337': ['*', [' ', ' '], '^8*6?3?a*[ab]b*2?0?1?$'],  # Media Type
    '338': ['*', [' ', ' '], '^8*6?3?a*[ab]b*2?0?1?$'],  # Carrier Type
    '340': ['*', [' ', ' '], '^8*6?3?[abcdefghijklmnopq]+2?0?1?$'],  # Physical Medium
    '341': ['*', [' 01', ' '], '^8*6?3?ab*c*d*e*2?0?1?$'],  # Accessibility Content
    '342': ['*', ['01', '012345678'], '^8*6?(([abcdghijklmnopqrstuvw])(?!.*\2)|[ef])+2?$'],  # Geospatial Reference Data
    '343': ['*', [' ', ' '], '^8*6?(([abcdefghi])(?!.*\2))+2?$'],  # Planar Coordinate Data
    '344': ['*', [' ', ' '], '^8*6?3?(?=[abcdeghhij])a*b*c*d*e*f*g*h*i*j*2?0?1?$'],  # Sound Characteristics
    '345': ['*', [' ', ' '], '^8*6?3?(?=[abcd])a*b*c*d*2?0?1?$'],  # Projection Characteristics of Moving Image
    '346': ['*', [' ', ' '], '^8*6?3?[ab]*?2?0?1?$'],  # Video Characteristics
    '347': ['*', [' ', ' '], '^8*6?3?(?=[abcdef])a*b*c*d*e*f*2?0?1?$'],  # Digital File Characteristics
    '348': ['*', [' ', ' '], '^8*6?3?(?=[abcd])(a*b*|c*d*)2?0?1?7*$'],  # Notated Music Characteristics
    '350': ['?', [' ', ' '], '^6?a+b*$'],  # Price
    '351': ['*', [' ', ' '], '^8*6?3?c?a*[ab]b*$'],  # Organization and Arrangement of Materials
    '352': ['*', [' ', ' '], '^8*6?a(bc?)*(def?)?g?i?q?$'],  # Digital Graphic Representation
    '353': ['*', [' ', ' '], '^8*6?3?(ab?|a?b)*2?0?1?$'],  # Supplementary Content Characteristics
    '355': ['*', ['0123458', ' '], '^8*6?ab*c*d?e?f?g?h?j*$'],  # Security Classification Control
    '357': ['?', [' ', ' '], '^8*6?ab*c*g*$'],  # Originator Dissemination Control
    '359': ['*', [' ', ' '], '^a$'],  # Rental Price
    '361': ['*', [' 01', ' '], '^8*6?3?o*5?y?s?a0*1*f*7*k?l?x*z*u*$'],  # Structured Ownership and Custodial History
    '362': ['*', [' 01', ' '], '^8*6?az?$'],  # Dates of Publication and/or Sequential Designation
    '363': ['*', [' 01', ' 01'], '^8*6?a(b(c(d(ef?)?)?)?)?(gh?)?(i(j(kl?)?)?)?m?u?((?<=i.*)v)?x*z*$'],
    # Normalized Date and Sequential Designation
    '365': ['*', [' ', ' '], '^8*6?ab?c?d?e?f?g?m?j?(hi?)?k?2?$'],  # Trade Price
    '366': ['*', [' ', ' '], '^8*6?(?=[abcdefg])a?b?c?d?e?f?g?j?k?m?2?$'],  # Trade Availability Information
    '370': ['*', [' ', ' '], '^8*6?3?i*[cfg]*(st?)?u*v*4*2?0?1?7*$'],  # Associated Place
    '377': ['*', [' ', ' 7'], '^8*6?3?(a*[al]l*0?1?)+2?7*$'],  # Associated Language
    '380': ['*', [' ', ' '], '^8*6?3?a+?2?0*1*7*$'],  # Form of Work
    '381': ['*', [' ', ' '], '^8*6?3?a+u?v?2?0?1?7*$'],  # Other Distinguishing Characteristics of Work or Expression
    '382': ['*', [' 0123', ' 01'], '^8*6?3?([abdp][en]?)+r?s?t?v*2?0*1*7*$'],  # Medium of Performance
    '383': ['*', [' 01', ' '], '^8*6?3?(?=[abc])a*b*c*((?<=c)d)?e?2?$'],
    # Numeric Designation of Musical Work or Expression
    '384': ['*', [' 012', ' '], '^8*6?3?a0*1*7*$'],  # Key
    '385': ['*', [' ', ' '], '^8*6?3?m?n?a*[ab]b*2?0*1*7*$'],  # Audience Characteristics
    '386': ['*', [' ', ' '], '^8*6?3?i*m?n?a*[ab]b*4*2?0*1*7*$'],  # Creator/Contributor Characteristics
    '387': ['*', [' ', ' '], '^8*6?3?(?=[abcdefghijklm])a*b*c*d*e*f*g*h*i*j*k*l*m*2?0*1*7*$'],
    # Representative Expression Characteristics
    '388': ['*', [' 12', ' '], '^8*6?3?a+2?0*1*7*$'],  # Time Period of Creation
    '400': ['*', ['0123', '01'], '^8*6?ab?q?c?d?c?u?t?[np]*[lf]*k?[lf]*x*v*e*4*$'],
    # Series Statement/Added Entry--Personal Name
    '410': ['*', ['012', '01'], '^8*6?ab*u?t?[np]*d?c?[np]*g?[lf]*k?[lf]*[np]*x*v*e*4*$'],
    # Series Statement/Added Entry--Corporate Name
    '411': ['*', ['012', '01'], '^8*6?aq?e*u?t?[np]*d?c?[np]*g*[lk]*f?[lk]*[np]*e*x*v*j*4*$'],
    # Series Statement/Added Entry--Meeting Name
    '440': ['*', [' ', '0123456789'], '^8*6?a[np]*x?v?w*0*$'],  # Series Statement/Added Entry--Title
    '490': ['*', ['01', ' '], '^8*6?3?(a+[xyz]v*)+l?7*$'],  # Series Statement
    '500': ['*', [' ', ' '], '^8*6?3?a5?7*$'],  # General Note
    '501': ['*', [' ', ' '], '^8*6?3?a5?7*$'],  # With Note
    '502': ['*', [' ', ' '], '^8*6?3?(a|g*bc?d?g*)o*7*$'],  # Dissertation Note
    '503': ['*', [' ', ' '], '^6?a$'],  # Bibliographic History Note
    '504': ['*', [' ', ' '], '^8*6?ab?$'],  # Bibliography, Etc. Note
    '505': ['*', ['0128', ' 0'], '^8*6?(a|(g?tg?r?g?)+|u)u*7*$'],  # Formatted Contents Note
    '506': ['*', [' 01', ' '], '^8*6?3?(?=[afu])(a?b*c*d*e*f*g*q?u*)2?5?$'],  # Restrictions on Access Note
    '507': ['?', [' ', ' '], '^8*6?3?(a|b|ab)$'],  # Scale Note for Visual Materials
    '508': ['*', [' ', ' '], '^8*6?a7*$'],  # Creation/Production Credits Note
    '509': ['*', [' ', ' '], '^a$'],  # Informal Notes (ESTC)
    '510': ['*', ['01234', ' '], '^8*6?3?au?x?b?(cu?)?7*$'],  # Citation/References Note
    '511': ['*', ['01', ' '], '^8*6?a$'],  # Participant or Performer Note
    '512': ['*', [' ', ' '], '^6?a$'],  # Earlier Or Later Volumes Separately Cataloged Note
    '513': ['*', [' ', ' '], '^8*6?ab?$'],  # Type of Report and Period Covered Note
    '514': ['?', [' ', ' '], '^8*6?z*(?=[abdefgijmu])a?b*c*d?e?f?g*h*i?j*k*m?u*$'],  # Data Quality Note
    '515': ['*', [' ', ' '], '^8*6?a7*$'],  # Numbering Peculiarities Note
    '516': ['*', [' 8', ' '], '^8*6?a$'],  # Type of Computer File or Data Note
    '517': ['?', [' 01', ' '], '^[ab]b*c*$'],  # Categories of Films Note (Archival)
    '518': ['*', [' ', ' '], '^8*6?3?(a|o*(o*d?(pd?2?0?1?)?)+)7*$'],  # Date/Time and Place of an Event Note
    '520': ['*', [' 012348', ' '], '^8*6?3?(ab?c?|u)u*((?<=a.*)2)?7*$'],  # Summary, Etc.
    '521': ['*', [' 012348', ' '], '^8*6?3?a+b?$'],  # Target Audience Note
    '522': ['*', [' 8', ' '], '^8*6?a$'],  # Geographic Coverage Note
    '523': ['?', [' ', ' '], '^6?ab?$'],  # Time Period of Content Note
    '524': ['*', [' 8', ' '], '^8*6?3?a2?$'],  # Preferred Citation of Described Materials Note
    '525': ['*', [' ', ' '], '^8*6?a$'],  # Supplement Note
    '526': ['*', ['08', ' '], '^8*6?3?i?ab?c?d?x*z*5?$'],  # Study Program Information Note
    '527': ['?', [' ', ' '], '^6?a$'],  # Censorship Note
    '530': ['*', [' ', ' '], '^8*6?3?ab?d?c?u*$'],  # Additional Physical Form Available Note
    '532': ['*', ['0128', ' '], '^8*6?3?a$'],  # Accessibility Note
    '533': ['*', [' ', ' '], '^8*6?3?am*b*c*d?e?f*7?n*5?y*$'],  # Reproduction Note
    '534': ['*', [' ', ' '], '^8*6?3?p?n*(?=[actkl])a?n*(t?c?|c?t?)b?f*k*l?e?m?n*o*x*z*$'],  # Original Version Note
    '535': ['*', ['12', ' '], '^8*6?3?ab*c*d*g?$'],  # Location of Originals/Duplicates Note
    '536': ['*', [' ', ' '], '^8*6?(?=[abcdefgh])a?b*c*d*e*f*g*h*$'],  # Funding Information Note
    '537': ['?', [' 8', ' '], '^6?a$'],  # Source of Data Note
    '538': ['*', [' ', ' '], '^8*6?3?a(i?u+)?5?$'],  # System Details Note
    '539': ['*', [' ', ' '], '^a$'],  # Location of Filmed Copy (ESTC)
    '540': ['*', [' ', ' '], '^8*6?3?ab?c?d?(f+2?)?g*q?u*5?$'],  # Terms Governing Use and Reproduction Note
    '541': ['*', [' 01', ' '], '^8*6?3?(([abcdefhno])(?!.*\2)|[no])+5?$'],  # Immediate Source of Acquisition Note
    '542': ['*', [' 01', ' '], '^8*6?3?(?=[acdfgl])a?b?c?d*e*f*g?h*i?j?k*l?m?n*o?p*q?r?s?u*$'],
    # Information Relating to Copyright Status
    '543': ['*', [' ', ' '], '^6?a$'],  # Solicitation Information Note
    '544': ['*', [' 01', ' '], '^8*6?3?(?=[dan])d*e*a*b*c*n*$'],  # Location of Other Archival Materials Note
    '545': ['*', [' 01', ' '], '^8*6?ab?u*$'],  # Biographical or Historical Data
    '546': ['*', [' ', ' '], '^8*6?3?ab*7*$'],  # Language Note
    '547': ['*', [' ', ' '], '^8*6?a$'],  # Former Title Complexity Note
    '550': ['*', [' ', ' '], '^8*6?a7*$'],  # Issuing Body Note
    '552': ['*', [' ', ' '], '^8*6?z*(?=[aceghjlou])a?b?c?d?e*f*g?h?i?j?k?l?m?n?o*p*u*$'],
    # Entity and Attribute Information Note
    '555': ['*', [' 08', ' '], '^8*6?3?(?=[adu])a?b*c?d?u*7*$'],  # Cumulative Index/Finding Aids Note
    '556': ['*', [' 8', ' '], '^8*6?az*$'],  # Information about Documentation Note
    '561': ['*', [' 01', ' '], '^8*6?3?[au]u*5?$'],  # Ownership and Custodial History
    '562': ['*', [' ', ' '], '^8*6?3?(?=[abc])a*b*c*[de]*5?$'],  # Copy and Version Identification Note
    '563': ['*', [' ', ' '], '^8*6?3?[au]u*5?$'],  # Binding Information
    '565': ['*', [' 08', ' '], '^8*6?3?ab*c*d*e8$'],  # Case File Characteristics Note
    '567': ['*', [' 8', ' '], '^8*6?(a|a?(b0?1?)+2)$'],  # Methodology Note
    '570': ['*', [' ', ' '], '^6?az?$'],  # Editor Note
    '580': ['*', [' ', ' '], '^8*6?a5?$'],  # Linking Entry Complexity Note
    '581': ['*', [' 8', ' '], '^8*6?3?az*$'],  # Publications About Described Materials Note
    '582': ['*', [' 8', ' '], '^6?a$'],  # Related Computer Files Note
    '583': ['*', [' 01', ' '], '^8*6?3?(no)*ab*c*d*e*f*h*i*j*k*l*u*x*z*2?5?7*$'],  # Action Note
    '584': ['*', [' ', ' '], '^8*6?3?a*[ab]b*5?$'],  # Accumulation and Frequency of Use Note
    '585': ['*', [' ', ' '], '^8*6?3?a5?$'],  # Exhibitions Note
    '586': ['*', [' 8', ' '], '^8*6?3?a$'],  # Awards Note
    '588': ['*', [' 01', ' '], '^8*6?a5?$'],  # Source of Description Note
    '590': ['*', [' ', ' '], '^a$'],  # Document Supply General Note
    '591': ['*', [' ', ' '], '^a$'],  # Document Supply Conference Note
    '592': ['*', [' ', ' '], '^a+$'],  # Collaboration Note
    '594': ['*', [' ', ' '], '^(ab?|a?b)$'],  # Reference to Items in Printed Catalogues
    '595': ['*', [' ', ' '], '^a$'],  # Document Supply Bibliographic History Note
    '596': ['*', [' ', ' '], '^a$'],  # Temporary Note
    '597': ['*', [' ', ' '], '^(ab?|a?b)$'],  # Editing or Error Message - Bibliographic (Migration)
    '598': ['*', [' ', ' '], '^a$'],  # Document Supply Selection / Ordering Information
    '599': ['*', [' ', ' '], '^a$'],  # Notes Relating to an Original (RPS)
    '600': ['*', ['013', '01234567'], '^8*6?3?a(([bdfhloqrtu])(?!.*\2)|[cgjkmnps])+[vxyz]*e*2?4*0?1?7*$'],
    # Subject Added Entry - Personal Name
    '610': ['*', ['012', '01234567'], '^8*6?3?ab*(([fhloqrtu])(?!.*\2)|[cdgjkmnps])+[vxyz]*e*2?4*0?1?7*$'],
    # Subject Added Entry - Corporate Name
    '611': ['*', ['012', '01234567'], '^8*6?3?a(([fhlqtu])(?!.*\2)|[cdegkmnps])+[vxyz]*j*2?4*0?1?7*$'],
    # Subject Added Entry - Meeting Name
    '630': ['*', ['0123456789', '01234567'], '^8*6?3?a(([fhlort])(?!.*\2)|[dgkmnps])+[vxyz]*e*2?4*0?1?7*$'],
    # Subject Added Entry - Uniform Title
    '647': ['*', [' ', '01234567'], '^8*6?3?ac*d?g*[vxyz]*e*2?4*0?1?7*$'],  # Subject Added Entry - Named Event
    '648': ['*', [' ', '01234567'], '^8*6?3?a[vxyz]*e*2?4*0?1?7*$'],  # Subject Added Entry - Chronological Term
    '650': ['*', [' 012', '01234567'], '^8*6?3?ab?c?d?g*[vxyz]*e*2?4*0?1?7*$'],  # Subject Added Entry - Topical Term
    '651': ['*', [' ', '01234567'], '^8*6?3?ag*[vxyz]*e*2?4*0?1?7*$'],  # Subject Added Entry - Geographic Name
    '652': ['*', [' ', ' '], '^a[xyz]*$'],  # Subject Added Entry - Reversed Geographic
    '653': ['*', [' 012', ' 0123456'], '^8*6?a+5?0?1?7*$'],  # Index Term - Uncontrolled
    '654': ['*', [' 012', ' '], '^8*6?3?(c[ab])+[vyz]*e*2?0?1?$'],  # Subject Added Entry - Faceted Topical Terms
    '655': ['*', [' 0', '01234567'], '^8*6?3?c?a(c?b)*[vxyz]*2?5?0?1?7*$'],  # Index Term - Genre/Form
    '656': ['*', [' ', '7'], '^8*6?3?ak?[vxyz]*2?0?1?$'],  # Index Term - Occupation
    '657': ['*', [' ', '7'], '^8*6?3?a[vxyz]*2?0?1?$'],  # Index Term - Function
    '658': ['*', [' ', ' '], '^8*6?3?ab*c?d?2?0?1?$'],  # Index Term - Curriculum Objective
    '662': ['*', [' ', ' '], '^8*6?((?=[abcdfg])a*b?c*d?f*g*|h+)e*2?4*0?1?$'],
    # Subject Added Entry - Hierarchical Place Name
    '688': ['*', [' ', ' 7'], '^8*6?3?ag*e*2?4*0?1?$'],  # Subject Added Entry - Type of Entity Unspecified
    '690': ['*', [' 7', ' '], '^a2?$'],  # Collection Subset
    '692': ['*', [' ', ' '], '^[abcefgi]p?$'],  # Nineteenth Century Subject Series Field
    '700': ['*', ['013', ' 2'], '^8*6?3?a(([bdfhloqrtux])(?!.*\2)|[cgijkmnps])+e*2?4*5?0?1?7*$'],
    # Added Entry - Personal Name
    '705': ['*', ['0123', '012'], '^a(([bdfhlort])(?!.*\2)|[cgkmnps])+e*$'],  # Added Entry -  Personal Name (Performer)
    '710': ['*', ['012', ' 2'], '^8*6?3?ab*(([fhlortux])(?!.*\2)|[cdgikmnp])+e*2?4*5?0?1?7*$'],
    # Added Entry - Corporate Name
    '711': ['*', ['012', ' 2'], '^8*6?3?a(([fhlqtux])(?!.*\2)|[cdegiknps])+j*2?4*5?0?1?7*$'],
    # Added Entry - Meeting Name
    '715': ['*', ['012', '012'], '^ab*(([fhlorstu])(?!.*\2)|[gkmnp])+e*$'],
    # Added Entry - Corporate Name (Performing Group)
    '720': ['*', [' 12', ' '], '^8*6?ae*2?4*5?0?1?7*$'],  # Added Entry - Uncontrolled Name
    '730': ['*', ['0123456789', ' 2'], '^8*6?3?a(([fhlortx])(?!.*\2)|[dgikmnps])+e*2?4*5?0?1?7*$'],
    # Added Entry - Uniform Title
    '740': ['*', ['0123456789', ' 2'], '^8*6?ah?[np]*5?$'],  # Added Entry - Uncontrolled Related/Analytical Title
    '751': ['*', [' ', ' '], '^8*6?3?ag*e*2?4*0?1?7*$'],  # Added Entry - Geographic Name
    '752': ['*', [' ', ' '], '^8*6?((?=[abcdfg])a*b?c*d?f*g*|h+)e*2?4*0?1?$'],  # Added Entry - Hierarchical Place Name
    '753': ['*', [' ', ' '], '^8*6?(?=[abc])a?b?c?2?0?1?$'],  # System Details Access to Computer Files
    '754': ['*', [' ', ' '], '^8*6?(ca)+d*x*z*2?0?1?$'],  # Added Entry - Taxonomic Identification
    '755': ['*', [' ', ' '], '^8*6?3?a[xyz]*2?$'],  # Added Entry - Physical Characteristics
    '758': ['*', [' ', ' '], '^8*6?3?4*i*a2?0?1?$'],  # Resource Identifier
    '760': ['*', ['01', ' 8'], '^8*6?a(([bcdhlmstxy])(?!.*\2)|[gimow])+4*0?1?l*$'],  # Main Series Entry
    '762': ['*', ['01', ' 8'], '^8*6?a(([bcdhlmstxy])(?!.*\2)|[gimow])+4*0?1?l*$'],  # Subseries Entry
    '765': ['*', ['01', ' 8'], '^8*6?a(([bcdhlmstuxy])(?!.*\2)|[gikmorwz])+4*0?1?l*$'],  # Original Language Entry
    '767': ['*', ['01', ' 8'], '^8*6?a(([bcdhlmstuxy])(?!.*\2)|[gikmorwz])+4*0?1?l*$'],  # Translation Entry
    '770': ['*', ['01', ' 8'], '^8*6?a(([bcdhlmstuxy])(?!.*\2)|[gikmorwz])+4*0?1?l*$'],
    # Supplement/Special Issue Entry
    '772': ['*', ['01', ' 08'], '^8*6?a(([bcdhlmstuxy])(?!.*\2)|[gikmorwz])+4*0?1?l*$'],  # Supplement Parent Entry
    '773': ['*', ['01', ' 8'], '^8*6?3?a(([bdhlmpqstuxy])(?!.*\2)|[gikmorwz])+4*5?0?1?l*$'],  # Host Item Entry
    '774': ['*', ['01', ' 8'], '^8*6?a(([bcdhlmstuxy])(?!.*\2)|[gikmorwz])+4*5?0?1?l*$'],  # Constituent Unit Entry
    '775': ['*', ['01', ' 8'], '^8*6?a(([bcdefhlmstuxy])(?!.*\2)|[gikmorwz])+4*0?1?l*$'],  # Other Edition Entry
    '776': ['*', ['01', ' 8'], '^8*6?a(([bcdhlmstuxy])(?!.*\2)|[gikmorwz])+4*0?1?l*$'],
    # Additional Physical Form Entry
    '777': ['*', ['01', ' 8'], '^8*6?a(([bcdhlmstuxy])(?!.*\2)|[gikmorwz])+4*0?1?l*$'],  # Issued With Entry
    '780': ['*', ['01', '01234567'], '^8*6?a(([bcdhlmstuxy])(?!.*\2)|[gikmorwz])+4*0?1?l*$'],  # Preceding Entry
    '785': ['*', ['01', '012345678'], '^8*6?a(([bcdhlmstuxy])(?!.*\2)|[gikmorwz])+4*0?1?l*$'],  # Succeeding Entry
    '786': ['*', ['01', ' 8'], '^8*6?a(([bcdhlmpstuvxy])(?!.*\2)|[gijkmorwz])+4*0?1?l*$'],  # Data Source Entry
    '787': ['*', ['01', ' 8'], '^8*6?a(([bcdhlmstuxy])(?!.*\2)|[gikmorwz])+4*5?0?1?l*$'],  # Other Relationship Entry
    '788': ['*', ['01', ' 8'], '^8*6?a(([bdestx])(?!.*\2)|[inw])+4*5?l*$'],
    # Parallel Description in Another Language of Cataloging
    '800': ['*', ['013', ' '], '^8*6?3?7?a(([bdfhloqrtux])(?!.*\2)|[cgikmnps])+v?w*e*2?4*5?0?1?$'],
    # Series Added Entry - Personal Name
    '810': ['*', ['012', ' '], '^8*6?3?ab*(([fhlortux])(?!.*\2)|[cdgikmnp])+v?w*e*2?4*5?0?1?7*$'],
    # Series Added Entry - Corporate Name
    '811': ['*', ['012', ' '], '^8*6?3?a(([fhlqtux])(?!.*\2)|[cdegiknps])+v?w*j*2?4*5?0?1?7*$'],
    # Series Added Entry - Meeting Name
    '830': ['*', [' ', '0123456789'], '^8*6?3?a(([fhlortx])(?!.*\2)|[dgikmnps])+v?w*e*2?4*5?0?1?7*$'],
    # Series Added Entry - Uniform Title
    '840': ['*', [' ', '0123456789'], '^ah?v?$'],  # Series Added Entry - Title
    '841': ['?', ['0', '0'], '^ab?e?$'],  # Holdings Coded Data Values
    '842': ['?', ['0', '0'], '^8*6?a$'],  # Textual Physical Form Designator
    '843': ['*', ['0', '0'], '^8*6?3?ab*c*d?e?f*m*n*7*5?$'],  # Reproduction Note
    '844': ['?', ['0', '0'], '^8*6?a$'],  # Name of Unit
    '845': ['*', ['0', '0'], '^8*6?3?ab?c?d?f*g*q?u*2?5?$'],  # Terms Governing Use and Reproduction
    '850': ['*', [' ', ' '], '^8*a+$'],  # Holding Institution
    '851': ['*', [' ', ' '], '^6?3?a+b?c?d?e?fg?$'],  # Location
    '852': ['*', [' 012345678', ' 012'], '^8*6?3?(a[fg]?)(b[fg]?)*(c[fg]?)*d*e*h?i*j?k*l?m*n?p?q?s*t?u*x*z* 2?$'],
    # Location
    '853': ['*', ['0', '0'],
            '^8*6?ao?(bu?v?o?(cu?v?o?(du?v?o?(eu?v?o?(fu?v?o?)?)?)?)?)?(go?(hu?v?o?)?)?z*(io?(jo?(ko?(lo?)?)?)?)?m?z*(p?wz?)?y*n?x*t?$'],
    # Captions and Pattern - Basic Bibliographic Unit
    '854': ['*', ['0', '0'],
            '^8*6?ao?(bu?v?o?(cu?v?o?(du?v?o?(eu?v?o?(fu?v?o?)?)?)?)?)?(go?(hu?v?o?)?)?z*(io?(jo?(ko?(lo?)?)?)?)?m?z*(p?wz?)?y*n?x*t?$'],
    # Captions and Pattern - Supplementary Material
    '855': ['*', ['0', '0'],
            '^8*6?ao?(bu?v?o?(cu?v?o?(du?v?o?(eu?v?o?(fu?v?o?)?)?)?)?)?(go?(hu?v?o?)?)?z*(io?(jo?(ko?(lo?)?)?)?)?m?z*(p?wz?)?y*n?x*t?$'],
    # Captions and Pattern - Indexes
    '856': ['*', [' 012347', ' 012348'],
            '^8*6?3?z*(?=.*[adflu])a+c*d*e*f*g*h*l*m*n*o?p?q*r*s*t*q*(uy?)*q*v*w*x*z* 2?7?$'],
    # Electronic Location and Access
    '857': ['*', [' 147', ' 012348'], '^8*6?3?z*(?=.*[bgu])b?c?d?f?g*h*l*m*n*q*r*s*t*q*(uy?)*q*x*z*2?7?5?e*$'],
    # Electronic Archive Location and Access
    '859': ['*', [' ', ' '], '^ab+$'],  # Digital Resource Flag
    '863': ['*', ['0', '0'], '^8*6?ao?(bo?(co?(do?(eo?(fo?)?)?)?)?)?(go?(ho?)?)?z*(i(j(k(l)?)?)?)?m?n?p?q?s*t?w?x*z*$'],
    # Enumeration and Chronology - Basic Bibliographic Unit
    '864': ['*', ['0', '0'], '^8*6?ao?(bo?(co?(do?(eo?(fo?)?)?)?)?)?(go?(ho?)?)?z*(i(j(k(l)?)?)?)?m?n?p?q?s*t?w?x*z*$'],
    # Enumeration and Chronology - Supplementary Material
    '865': ['*', ['0', '0'], '^8*6?ao?(bo?(co?(do?(eo?(fo?)?)?)?)?)?(go?(ho?)?)?z*(i(j(kl?)?)?)?v*m?n?p?q?s*t?w?x*z*$'],
    # Enumeration and Chronology - Indexes
    '866': ['*', ['0', '0'], '^8*6?ax*z*2?$'],  # Textual Holdings - Basic Bibliographic Unit
    '867': ['*', ['0', '0'], '^8*6?ax*z*2?$'],  # Textual Holdings - Supplementary Material
    '868': ['*', ['0', '0'], '^8*6?ax*z*2?$'],  # Textual Holdings - Indexes
    '870': ['*', ['0123', '012'], '^a(([bdfhloqrtux])(?!.*\2)|[cgijkmnps])+e*2?4*5?$'],  # Variant Personal Name
    '871': ['*', ['012', '012'], '^ab*(([fhlortux])(?!.*\2)|[cdgikmnp])+e*2?4*5?$'],  # Variant Corporate Name
    '872': ['*', ['012', '012'], '^a(([fhlqtux])(?!.*\2)|[cdegiknps])+j*2?4*5?$'],  # Variant Conference Or Meeting Name
    '873': ['*', ['0123456789', '012'], '^a(([fhlortx])(?!.*\2)|[dgikmnps])+e*2?4*5?$'],
    # Variant Uniform Title Heading
    '876': ['*', ['0', '0'], '^8*6?3?ab*c*d*e*h*j*l*p*r*tx*z*$'],  # Item Information - Basic Bibliographic Unit
    '877': ['*', ['0', '0'], '^8*6?3?ab*c*d*e*h*j*l*p*r*tx*z*$'],  # Item Information - Supplementary Material
    '878': ['*', ['0', '0'], '^8*6?3?ab*c*d*e*h*j*l*p*r*tx*z*$'],  # Item Information - Indexes
    '880': ['*', [' 0123456789', ' 0123456789'], '^8*63?[a-z]+[0-9]*$'],  # Alternate Graphic Representation
    '881': ['*', [' ', ' '], '^8*6?3?[abcdefghijklmn]+$'],  # Manifestation Statements
    '882': ['?', [' ', ' '], '^8*6?i*a*i*w+$'],  # Replacement Record Information
    '883': ['*', [' 012', ' '], '^8*(au?|a?u)d?x?q?c?w*0*1*$'],  # Metadata Provenance
    '884': ['*', [' ', ' '], '^ag?k?q?u*$'],  # Description Conversion Information
    '885': ['*', [' ', ' '], '^aw+bc?d?x*z*2?5?0*1*$'],  # Matching Information
    '886': ['*', ['012', ' '], '^2?ab[a-z0-9]+$'],  # Foreign MARC Information Field
    '887': ['*', [' ', ' '], '^2?a$'],  # Non-MARC Information Field
    '909': ['?', [' ', ' '], '^(ab?|a?b)$'],  # Awaiting OCLC Upgrade
    '916': ['?', [' ', ' '], '^a+$'],  # Authority Control Information
    '917': ['?', [' ', ' '], '^a$'],  # Production Category
    '945': ['*', [' 1', ' '], '^a$'],  # BL Local Title
    '950': ['*', [' ', ' '], '^(a+x*y*z*)(sa+x*y*z*)+$'],  # Library of Congress Subject (Cross-Reference)
    '954': ['?', [' ', ' '], '^a$'],  # Transliteration Statement
    '955': ['*', [' ', ' '], '^ab?$'],  # Shelving Location
    '957': ['*', [' ', ' '], '^a+b*c*d*r?s*t?$'],  # Acquisitions Data
    '958': ['*', [' ', ' '], '^ac?$'],  # Superseded Shelfmark
    '959': ['*', [' ', ' '], '^f$'],  # Document Supply Status Flag
    '960': ['*', ['01', ' '], '^a$'],  # Normalized Place of Publication
    '961': ['*', [' ', ' '], '^ab?$'],  # Sheet Index Note
    '962': ['*', [' ', ' '], '^acf$'],  # Colindale Location Flag
    '963': ['*', [' ', ' '], '^ab?c$'],  # Cambridge University Library Location
    '964': ['*', [' ', ' '], '^acd?e?$'],  # Science Museum Library Location
    '966': ['*', [' ', ' '], '^ul$'],  # Document Supply Acquisitions Indicator
    '968': ['*', [' ', ' '], '^[abc]$'],  # Record Status Field
    '970': ['*', [' ', ' '], '^a$'],  # Collection Code
    '975': ['?', [' ', ' '], '^(ab?|a?b)$'],  # Insufficient Record Statement
    '976': ['?', [' ', ' '], '^a$'],  # Non-monographic Conference Indicator
    '979': ['*', [' ', ' '], '^.*$'],  # Negative Shelfmark
    '980': ['?', [' ', ' '], '^a$'],  # Card Production Indicator
    '985': ['*', [' ', ' '], '^a$'],  # Cataloguer’s Note
    '990': ['*', [' ', ' '], '^a+$'],  # Product Information Code
    '992': ['*', [' ', ' '], '^a+$'],  # Stored Search Flag
    '996': ['?', [' ', ' '], '^a$'],  # Z39.50 SFX Enabler
    '997': ['*', [' ', ' '], '^a+$'],  # Shared Library Message Field
    'A02': ['*', [' ', ' '], '^az?$'],  # Serial Acquisitions System Number
    'ACF': ['*', [' ', ' '], '^8*6?3?ab?c?d?e?fg?h?i?u?5$'],  # Previous Copyright Fee Information
    'AQN': ['*', [' ', ' '], '^a$'],  # Acquisitions Notes Field
    'BGT': ['?', [' ', ' '], '^a$'],  # BGLT (British Grey Literature Team) Report Flag
    'BUF': ['?', [' 12', ' '], '^ad$'],  # Batch Upgrade Flag
    'CAT': ['*', [' ', ' '], '^abclh$'],  # Cataloguer
    'CFI': ['*', [' 012', ' '], '^8*6?3?ab?c?d?e?fg?h?i?u?5$'],  # Copyright Fee Information
    'CNF': ['?', [' ', ' '], '^ae*n?d?c?e*$'],  # Document Supply Conference Heading
    'DEL': ['?', [' ', ' '], '^a$'],  # Deleted
    'DGM': ['?', [' ', ' '], '^a$'],  # Digitised Record Match
    'DRT': ['*', [' ', ' '], '^a$'],  # Digital Record Type
    'EST': ['?', [' ', ' '], '^a$'],  # Document Supply ESTAR (Electronic Storage and Retrieval System) Flag
    'EXP': ['?', [' ', ' '], '^ad?$'],  # Block Export
    'FFP': ['?', [' ', ' '], '^ab?$'],  # Flag For Publication
    'FIN': ['?', [' 12', ' '], '^ad?$'],  # Finished (Cataloguing)
    'LAS': ['?', [' ', ' '], '^abclh$'],  # Last CAT Field
    'LCS': ['*', ['0', ' '], '^8*6?3?(a+[xyz]v*)+l?7*$'],  # Library of Congress Series Statement
    'LDO': ['*', [' ', ' '], '^ab?c?d?$'],  # LDO (Legal Deposit Office) Information
    'LEO': ['*', [' ', ' '], '^a$'],  # LEO (Library Export Operations) Identifier
    'LET': ['?', [' ', '0123456789'], '^a$'],  # Serials claim letter title
    'LKR': ['*', [' ', ' '], '^ablrm?n?p?y?v?i?k?$'],  # Link
    'MIS': ['?', [' ', ' '], '^a$'],  # Monograph in Series Flag
    'MNI': ['?', [' ', ' '], '^a$'],  # Medium-Neutral Identifier
    'MPX': ['?', [' ', ' '], '^a$'],  # Map Leader Data Element
    'NEG': ['?', [' ', ' '], '^a$'],  # LDO (Legal Deposit Office) Signoff
    'NID': ['?', [' ', ' '], '^a$'],  # Newspaper Identifier
    'NLP': ['?', [' ', ' '], '^a$'],  # Newspaper Programme Identifier
    'OBJ': ['?', [' ', ' '], '^a$'],  # Digital Object Field
    'OHC': ['?', [' ', ' '], '^a$'],  # Original Holding Count
    'ONS': ['*', [' ', ' 7'], '^(a[xt]?|t)2?$'],  # ONIX Subjects
    'ONX': ['*', [' ', ' '], '^(ab?c?|bc?|c)$'],  # ONIX Un-Mapped Data
    'PLR': ['?', [' ', ' '], '^ab?$'],  # PRIMO Large Record
    'RSC': ['?', [' ', ' '], '^a$'],  # Remote Supply Collection
    'SID': ['?', [' ', ' '], '^abc$'],  # Source ID
    'SRC': ['*', [' ', ' '], '^(ab?|b)$'],  # Source
    'SSD': ['*', [' ', ' '], '^a$'],  # STM Serials Designation
    'STA': ['?', [' ', ' '], '^ab$'],  # Status
    'TOC': ['?', [' ', ' '], '^a$'],  # Document Supply ETOC (Electronic Table of Contents) Flag
    'UNO': ['?', [' ', ' '], '^a$'],  # Unencrypted Download ID
    'VIT': ['*', [' ', ' '], '^bcdefg(ijk)?o?s?$'],  # Virtual Item

}


for field_tag in DATA_FIELDS:
    try:
        DATA_FIELDS[field_tag] = DataField(field_tag, *DATA_FIELDS[field_tag])
    except Exception as e:
        print(str(e))
        print(field_tag)


SUBFIELDS = {
    # ^8*(a(b*|z*)|b+|z+)$
    '010': {
        '010$8': ['*', '^8', '8abz'],
        '010$a': ['?', '^8', 'bz$'],
        '010$b': ['*', '^8ab', 'b$'],
        '010$z': ['*', '^8az', 'z$']
    },
    # ^8*6?ab?c?(de?)*f*$
    '013': {
        '013$8': ['*', '^8', '86a'],
        '013$6': ['?', '^8', 'a'],
        '013$a': ['1', '^86', 'bcdf$'],
        '013$b': ['?', 'a', 'cdf$'],
        '013$c': ['?', 'ab', 'df$'],
        '013$d': ['*', 'abcde', 'def$'],
        '013$e': ['*', 'd', 'df$'],
        '013$f': ['*', 'abcde', '$'],
    },
    # ^8*6?(a+|z)z*q*2?$
    '015': {
        '015$8': ['*', '^8', '86az'],
        '015$6': ['?', '^8', 'az'],
        '015$a': ['*', '^86a', 'azq2$'],
        '015$z': ['*', '^86az', 'zq2$'],
        '015$q': ['*', 'az', 'q2$'],
        '015$2': ['?', 'azq', '$'],
    },
    # ^8*[az]z*2?$
    '016': {
        '016$8': ['*', '^8', '8az'],
        '016$a': ['?', '^8', 'z2$'],
        '016$z': ['*', '^8az', 'z2$'],
        '016$2': ['?', '^az', '$'],
    },
    # 8*6?i?(a+|z)z*bd?2?$
    '017': {
        '017$8': ['*', '^8', '86iaz'],
        '017$6': ['?', '^8', 'iaz'],
        '017$i': ['?', '^86', 'az'],
        '017$a': ['*', '^86ia', 'azb'],
        '017$z': ['*', '^86iaz', 'zb'],
        '017$b': ['1', 'az', 'd2$'],
        '017$d': ['?', 'b', '2$'],
        '017$2': ['?', 'bd', '$'],
    },
    # ^8*6?a$
    '018': {
        '018$8': ['*', '^8', '86a'],
        '018$6': ['?', '^8', 'a'],
        '018$a': ['1', '^86', '$'],
    },
    # ^8*6?(a+|z)z*q*c?$
    '020': {
        '020$8': ['*', '^8', '86az'],
        '020$6': ['?', '^8', 'az'],
        '020$a': ['*', '^86a', 'azqc$'],
        '020$z': ['*', '^86az', 'zqc$'],
        '020$q': ['*', 'azq', 'qc$'],
        '020$c': ['?', 'azq', '$'],
    },
    # ^8*6?(((al?|l)m*|(m+|y))y*|z)z*2?0?1*$
    '022': {
        '022$8': ['*', '^8', '86almyz'],
        '022$6': ['?', '^8', 'almyz'],
        '022$a': ['?', '^86', 'lmz2'],
        '022$l': ['?', '^86a', 'mz2'],
        '022$m': ['*', '^86alm', 'myz2'],
        '022$y': ['*', '^86my', 'yz2'],
        '022$z': ['*', '^86almyz', 'z2'],
        '022$2': ['?', '^86almyz', '01$'],
        '022$0': ['?', '^86almyz2', '1$'],
        '022$1': ['*', '^86almyz201', '1$'],
    },
    # ^8*6?(ad?|zd?)(zd?)*q*c?2?$
    '024': {
        '024$8': ['*', '^8', '86az'],
        '024$6': ['?', '^8', 'az'],
        '024$a': ['1', '^86', 'zdqc2$'],
        '024$d': ['?', '^az', 'zqc2$'],
        '024$z': ['1', '^86adz', 'zdqc2$'],
        '024$q': ['*', 'adzq', '*qc2$'],
        '024$c': ['?', 'adzq', '2$'],
        '024$2': ['?', 'adzqc', '$'],
    },
    # ^8*a+$
    '025': {
        '025$8': ['*', '^8', '8a'],
        '025$a': ['+', '^8a', 'a$'],
    },
    # ^8*6?(abc?d*|e)2?5*$
    '026': {
        '026$8': ['*', '^8', '86ae'],
        '026$6': ['?', '^8', 'ae'],
        '026$a': ['?', '^86', 'b'],
        '026$b': ['?', 'a', 'cd25$'],
        '026$c': ['?', 'ab', 'd25$'],
        '026$d': ['*', 'bcd', 'd25$'],
        '026$e': ['?', '^86', '25$'],
        '026$2': ['?', 'bcde', '5$'],
        '026$5': ['*', 'bcde25', '5$'],
    },
    # ^8*6?[az]z*q*$
    '027': {
        '027$8': ['*', '^8', '86az'],
        '027$6': ['?', '^8', 'az'],
        '027$a': ['?', '^86', 'zq$'],
        '027$z': ['*', '^86az', 'zq$'],
        '027$q': ['*', 'azq', 'q$'],
    },
    # ^8*6?abq*$
    '028': {
        '028$8': ['*', '^8', '86a'],
        '028$6': ['?', '^8', 'a'],
        '028$a': ['1', '^86', 'b'],
        '028$b': ['1', 'a', 'q$'],
        '028$q': ['*', 'b', 'q$'],
    },
    # ^8*6?[az]z*$
    '030': {
        '030$8': ['*', '^8', '86az'],
        '030$6': ['?', '^8', 'az'],
        '030$a': ['?', '^86', 'z$'],
        '030$z': ['*', '^86az', 'z$'],
    },
    # ^8*6?abcm?e?d*t*r?g?n?o?t*p?u*q*s*y*z*2?$
    '031': {
        '031$8': ['*', '^8', '86'],
        '031$6': ['?', '^8', 'a'],
        '031$a': ['1', '^86', 'b'],
        '031$b': ['1', 'a', 'c'],
        '031$c': ['1', 'b', 'medtrgnopuqsyz2$'],
        '031$m': ['?', 'c', 'edtrgnopuqsyz2$'],
        '031$e': ['?', 'cm', 'dtrgnopuqsyz2$'],
        '031$d': ['*', 'cmd', 'dtrgnopuqsyz2$'],
        '031$t': ['*', 'cmdtrgno', 'trgnopuqsyz2$'],
        '031$r': ['?', 'cmdt', 'gnotpuqsyz2$'],
        '031$g': ['?', 'cmdtr', 'notpuqsyz2$'],
        '031$n': ['?', 'cmdtrg', 'otpuqsyz2$'],
        '031$o': ['?', 'cmdtrgn', 'tpuqsyz2$'],
        '031$p': ['?', 'cmdtrgno', 'uqsyz2$'],
        '031$u': ['*', 'cmdtrgnou', 'uqsyz2$'],
        '031$q': ['*', 'cmdtrgnouq', 'qsyz2$'],
        '031$s': ['*', 'cmdtrgnouqs', 'syz2$'],
        '031$y': ['*', 'cmdtrgnouqsy', 'yz2$'],
        '031$z': ['*', 'cmdtrgnouqsyz', 'z2$'],
        '031$2': ['?', 'cmdtrgnouqsyz', '$'],
    },
    # ^8*6?ab$
    '032': {
        '032$8': ['*', '^8', '86a'],
        '032$6': ['?', '^8', 'a'],
        '032$a': ['1', '^86', 'b'],
        '032$b': ['1', 'a', '$'],
    },
    # ^8*6?3?(a|(bc?)|p)+0*1*2?$
    '033': {
        '033$8': ['*', '^8', '863abp'],
        '033$6': ['?', '^8', '3abp'],
        '033$3': ['?', '^86', 'abp'],
        '033$a': ['*', '^863abcp', 'abp012$'],
        '033$b': ['*', '^863abcp', 'abcp012$'],
        '033$c': ['*', 'b', 'abp012$'],
        '033$p': ['*', '^863abcp', 'abp012$'],
        '033$0': ['*', 'abcp0', '012$'],
        '033$1': ['*', 'abcp01', '12$'],
        '033$2': ['?', 'abcp01', '$'],
    },
    '040': {
        '040$8': ['*', '^', '86a'],
        '040$6': ['?', '^8', 'a'],
        '040$a': ['1', '^86', 'b'],
        '040$b': ['1', 'a', 'cde$'],
        '040$c': ['?', 'b', 'de$'],
        '040$d': ['*', 'bcd', 'de$'],
        '040$e': ['?', 'bcde', 'e$'],
    },
}

for field_tag in SUBFIELDS:
    for full_tag in SUBFIELDS[field_tag]:
        SUBFIELDS[field_tag][full_tag] = Subfield(full_tag, *SUBFIELDS[field_tag][full_tag])
