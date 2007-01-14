#! /usr/bin/env python
# -*- coding: utf-8 -*-

#--------------------------------------------------------------------#
# This file is part of Py-notify.                                    #
#                                                                    #
# Copyright (C) 2007 Paul Pogonyshev.                                #
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


import unittest


def _load_all_tests ():
    test_suite = unittest.TestSuite ()

    for module_name in ('all', 'bind', 'condition', 'mediator', 'signal', 'variable'):
        module = __import__('test.%s' % module_name, globals (), locals (), ('*',))
        test_suite.addTest (unittest.defaultTestLoader.loadTestsFromModule (module))

    return test_suite


class AllTests (object):

    def __init__(self):
        self.load_all_tests = _load_all_tests


print 'Note that most of the time is spent in gc.collect() calls, not in this package\n'

unittest.main (AllTests (), 'load_all_tests')



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
