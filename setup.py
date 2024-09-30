#!/usr/bin/env python
# -*- coding: utf8 -*-

"""setup.py file for buzz."""

# Import required modules
from setuptools import setup, find_packages

print(str(find_packages()))
setup(name='buzz',
      version='2.0.0',
      author='Victoria Morris',
      author_email='victoria.morris@bl.uk',
      license='MIT License',
      description='Tools for checking and amending records in MARC21 format',
      long_description=
      '''Tools for checking and amending records in MARC21 format''',
      packages=find_packages(),
      platforms=['any'],
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Web Environment',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Natural Language :: English',
          'Programming Language :: Python'
          'Topic :: Internet :: Z39.50',
          'Topic :: Scientific/Engineering :: Information Science',
          'Topic :: Text Processing'
      ],
      url='https://github.com/victoriamorris/BUZZ',
      requires=['setuptools', 'Flask', 'regex', 'werkzeug']
      )
