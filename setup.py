#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Py-notify.
#
# Unlike the rest of Py-notify, it is explicitely put in Public Domain.  Use as you
# please.


# In particular, we heavily use True and False, there are uses of enumerate(), file coding
# is explicitly set etc.

REQUIRED_PYTHON_VERSION = (2, 3)



import sys
import os
import re


if sys.version_info[:3] < REQUIRED_PYTHON_VERSION:
    sys.exit ('%s: Python version %s is required'
              % (sys.argv[0],
                 '.'.join ([str (subversion) for subversion in REQUIRED_PYTHON_VERSION])))



if os.path.dirname (sys.argv[0]):
    os.chdir (os.path.dirname (sys.argv[0]))

if not os.path.isfile (os.path.join ('notify', 'all.py')):
    sys.exit ("%s: cannot find '%s', strange..."
              % (sys.argv[0], os.path.join ('notify', 'all.py')))



try:
    version_file = open ('version')

    try:
        version = version_file.readline ().strip ()
    finally:
        version_file.close ()

except IOError:
    sys.exit ('%s: error: %s' % (sys.argv[0], sys.exc_info () [1]))



def configure (version):
    configuration_parameters = { 'version_string': version,
                                 'version':        tuple (map (lambda string: int (string),
                                                               version.split ('.'))) }

    # This can be much simplified with Python 2.5 `with' statement, once that version is
    # required.

    try:
        template_file   = None
        output_file_in  = None
        output_file_out = None

        try:
            template_file    = open (os.path.join ('notify', '__init__.py.in'))
            result_line_list = []
            in_configuration = False

            for line in template_file:
                if re.search ('# *CONFIGURATION *$', line):
                    in_configuration = True
                elif re.search ('# */CONFIGURATION *$', line):
                    in_configuration = False
                else:
                    if in_configuration:
                        line = line % configuration_parameters

                result_line_list.append (line)

        finally:
            if template_file is not None:
                template_file.close ()

        output_file_name = os.path.join ('notify', '__init__.py')

        try:
            try:
                output_file_in = open (output_file_name, 'r')
            except IOError:
                # Cannot open, so ignore.
                pass
            else:
                if list (output_file_in) == result_line_list:
                    return

        finally:
            if output_file_in is not None:
                output_file_in.close ()

        try:
            output_file_out = open (output_file_name, 'w')
            output_file_out.writelines (result_line_list)

        finally:
            if output_file_out is not None:
                output_file_out.close ()

    except IOError:
        sys.exit (str (sys.exc_info () [1]))



configure (version)



long_description = \
"""
Py-notify is a Python package providing tools for implementing `Observer programming
pattern`_.  These tools include signals, conditions and variables.

Signals are lists of handlers that are called when signal is emitted. Conditions are
basically boolean variables coupled with a signal that is emitted when condition state
changes. They can be combined using standard logical operators (*not*, *and*, etc.) into
compound conditions. Variables, unlike conditions, can hold any Python object, not just
booleans, but they cannot be combined.

For more verbose introduction, please refer to the tutorial_.

.. _Observer programming pattern:
   http://en.wikipedia.org/wiki/Observer_pattern

.. _tutorial:
   http://home.gna.org/py-notify/tutorial.html
"""

classifiers = ['Topic :: Software Development :: Libraries :: Python Modules',
               'Intended Audience :: Developers',
               'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
               'Development Status :: 4 - Beta',
               'Operating System :: OS Independent',
               'Programming Language :: Python',
               'Programming Language :: C']



from distutils.core              import setup, Extension
from distutils.command.build_ext import build_ext as _build_ext

import distutils.util



class build_ext (_build_ext):

    def build_extension (self, extension):
        _build_ext.build_extension (self, extension)

        if not self.inplace and os.name == 'posix':
            filename        = self.get_ext_filename (extension.name)
            link_filename   = filename
            target_filename = os.path.join (self.build_lib, filename)

            recursion_scan  = os.path.split (filename) [0]

            if hasattr (os, 'symlink'):
                if (    os.path.islink (link_filename)
                    and os.path.realpath (link_filename) == os.path.abspath (target_filename)):
                    return

            while recursion_scan:
                recursion_scan  = os.path.split (recursion_scan) [0]
                target_filename = os.path.join  (os.pardir, target_filename)

            try:
                os.remove (link_filename)
            except:
                # Ignore all errors.
                pass

            if hasattr (os, 'symlink'):
                try:
                    os.symlink (target_filename, link_filename)
                except:
                    # Ignore all errors.
                    pass
            else:
                # FIXME: Copy the library then.
                pass



# Note: the goal of the below function and manipulation of distuils.util module contents
# is to not byte-compile files that use 2.5 features on earlier Python versions.  Python
# 2.3 will be baffled by function decorators already, 2.4 --- by `yield' inside `try
# ... finally'.

import __future__

def should_be_byte_compiled (filename):
    package_name = os.path.basename (os.path.split (filename) [0])
    return package_name != '_2_5' or 'with_statement' in __future__.all_feature_names

def custom_byte_compile (filenames, *arguments, **keywords):
    original_byte_compile ([filename for filename in filenames
                            if should_be_byte_compiled (filename)],
                           *arguments, **keywords)

original_byte_compile       = distutils.util.byte_compile
distutils.util.byte_compile = custom_byte_compile



gc_extension = Extension (name    = 'notify.gc',
                          sources = [os.path.join ('notify', 'gc.c')])



setup (name             = 'py-notify',
       version          = version,
       description      = 'An unorthodox implementation of Observer programming pattern.',
       long_description = long_description,
       author           = 'Paul Pogonyshev',
       author_email     = 'py-notify-dev@gna.org',
       url              = 'http://home.gna.org/py-notify/',
       download_url     = 'http://download.gna.org/py-notify/',
       license          = "GNU Lesser General Public License v2.1",
       classifiers      = classifiers,
       packages         = ['notify', 'notify._2_5'],
       ext_modules      = [gc_extension],
       cmdclass         = { 'build_ext': build_ext })



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
