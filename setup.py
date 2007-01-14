#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Py-notify.
#
# Unlike the rest of Py-notify, it is explicitely put in Public
# Domain.  Use as you please.


# In particular, we heavily use True and False, there are uses of
# enumerate(), file coding is explicitly set etc.
REQUIRED_PYTHON_VERSION = (2, 3)



import sys
import os
import re


if sys.version_info[:3] < REQUIRED_PYTHON_VERSION:
    sys.exit ('%s: Python version %s is required'
              % (sys.argv[0],
                 '.'.join ([str (subversion) for subversion in REQUIRED_PYTHON_VERSION])))



os.chdir (os.path.dirname (sys.argv[0]))

if not os.path.isfile (os.path.join ('notify', 'all.py')):
    sys.exit ("%s: cannot find `%s', strange..."
              % (sys.argv[0], os.path.join ('notify', 'all.py')))



try:
    version_file = open ('version')

    try:
        version = version_file.readline ().strip ()
    finally:
        version_file.close ()

except IOError, exception:
    sys.exit ('%s: error: %s' % (sys.argv[0], exception))



def configure (version):
    configuration_parameters = { 'version_string': version,
                                 'version':        tuple (map (lambda string: int (string),
                                                               version.split ('.'))) }

    try:
        template_file = open (os.path.join ('notify', '__init__.py.in'))

        try:
            output_file = open (os.path.join ('notify', '__init__.py'), 'w')

            try:
                in_configuration = False

                for line in template_file:
                    if re.search ('# *CONFIGURATION *$', line):
                        in_configuration = True
                    elif re.search ('# */CONFIGURATION *$', line):
                        in_configuration = False
                    else:
                        if in_configuration:
                            line = line % configuration_parameters

                    output_file.write (line)

            finally:
                output_file.close ()
        finally:
            template_file.close ()

    except IOError, exception:
        sys.exit (str (exception))



configure (version)



classifiers = ['Topic :: Software Development :: Libraries :: Python Modules',
               'Intended Audience :: Developers',
               'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
               'Development Status :: 3 - Alpha',
               'Operating System :: OS Independent',
               'Programming Language :: Python']



from distutils.core import *



setup (name         = 'py-notify',
       version      = version,
       description  = 'A Python package providing signals, conditions and variables.',
       author       = 'Paul Pogonyshev',
       author_email = 'py-notify-dev@gna.org',
       url          = 'http://home.gna.org/py-notify/',
       download_url = 'http://download.gna.org/py-notify/',
       license      = "GNU Lesser General Public License v2.1 (see `COPYING')",
       classifiers  = classifiers,
       packages     = ['notify'])



# Local variables:
# coding: utf-8
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# End:
