#! /usr/bin/env python
# -*- coding: utf-8 -*-

#--------------------------------------------------------------------#
# This file is part of Py-notify.                                    #
#                                                                    #
# Copyright (C) 2007, 2008 Paul Pogonyshev.                          #
#                                                                    #
# This library is free software; you can redistribute it and/or      #
# modify it under the terms of the GNU Lesser General Public License #
# as published by the Free Software Foundation; either version 2.1   #
# of the License, or (at your option) any later version.             #
#                                                                    #
# This library is distributed in the hope that it will be useful,    #
# but WITHOUT ANY WARRANTY; without even the implied warranty of     #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU  #
# Lesser General Public License for more details.                    #
#                                                                    #
# You should have received a copy of the GNU Lesser General Public   #
# License along with this library; if not, write to the Free         #
# Software Foundation, Inc., 51 Franklin Street, Fifth Floor,        #
# Boston, MA 02110-1301 USA                                          #
#--------------------------------------------------------------------#


import os
import sys
import unittest


if not os.path.isfile (os.path.join ('notify', 'all.py')):
    sys.exit ("%s: cannot find '%s', strange..."
              % (sys.argv[0], os.path.join ('notify', 'all.py')))



_extensions_built = False

def _build_extensions ():
    global _extensions_built

    if not _extensions_built:
        print ('Building extension...')

        # FIXME: Is that portable enough?
        if os.system ('python setup.py build_ext') != 0:
            sys.exit (1)

        _extensions_built = True



_TEST_MODULES = ('all', 'base', 'bind', 'condition', '_gc', 'mediator', 'signal',
                 'utils', 'variable')

def _import_module (module_name):
    _build_extensions ()
    return __import__('test.%s' % module_name, globals (), locals (), ('*',))

def _import_module_tests (module_name):
    return unittest.defaultTestLoader.loadTestsFromModule (_import_module (module_name))

def _import_all_tests ():
    everything = unittest.TestSuite ()
    for module_name in _TEST_MODULES:
        everything.addTest (_import_module_tests (module_name))

    return everything


class _TestModuleImporter (object):

    def __init__(self, module_name):
        self._module_name = module_name

    def __call__(self):
        return _import_module_tests (object.__getattribute__(self, '_module_name'))

    def __getattribute__(self, name):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return getattr (_import_module (object.__getattribute__(self, '_module_name')), name)


class AllTests (object):

    def __init__(self):
        self.everything = _import_all_tests
        for module_name in _TEST_MODULES:
            setattr (self, module_name, _TestModuleImporter (module_name))


class TestProgram (unittest.TestProgram):

    def runTests (self):
        _build_extensions ()

        print ('\nNote that almost all time is spent in gc.collect() calls, not in this package\n')
        unittest.TestProgram.runTests (self)



TestProgram (AllTests (), 'everything')



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
