#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ====================
#       Set-up
# ====================

# Import required modules
import datetime
import re
import sys
import unicodedata

__author__ = 'Victoria Morris'
__license__ = 'MIT License'
__version__ = '1.0.0'
__status__ = '4 - Beta Development'


# ====================
#      Constants
# ====================


NODE_TYPES = ['string', 'isbn']


# ====================
#  General functions
# ====================


def clean(string):
    if string is None or not string: return None
    string = re.sub(r'[\u0022\u055A\u05F4\u2018-\u201F\u275B-\u275E\uFF07]', '\'', string)
    string = re.sub(r'[\u0000-\u001F\u0080-\u009F\u2028\u2029]+', '', string)
    string = re.sub(r'^[:;/\s?\$.,\\\]\)}]|[;/\s\$\.,\\\[\({]+$', '', string.strip())
    string = re.sub(r'\s+', ' ', string).strip()
    if string is None or not string: return None
    return unicodedata.normalize('NFC', string)


def message(s) -> str:
    """Function to convert OPTIONS description to present tense"""
    if s == 'Exit program': return 'Shutting down'
    return s.replace('Parse', 'Parsing').replace('EXport', 'Exporting').replace('Search', 'Searching').replace('Add', 'Adding')


def is_null(var) -> bool:
    """Function to test whether a variable is null"""
    if var is None or not var: return True
    if isinstance(var, (str, list, tuple, set)) and len(var) == 0: return True
    if isinstance(var, str) and var == '': return True
    if isinstance(var, (int, float, complex, bool)) and int(var) == 0: return True
    return False


def which(s, l):
    """Function to determine which member of a list is a substring of a given string
    (returns the first list item with this property,
    so not useful if the string contains more than one list item)"""
    for i in l:
        if i in s: return i
    return None


def date_time(message=None):
    if message:
        print('\n\n{} ...'.format(message))
        print('----------------------------------------')
    print(str(datetime.datetime.now()))


def date_time_exit():
    date_time(message='All processing complete')
    sys.exit()


def exit_prompt(message=None):
    """Function to exit the program after prompting the use to press Enter"""
    if message: print(str(message))
    input('\nPress [Enter] to exit...')
    sys.exit()
