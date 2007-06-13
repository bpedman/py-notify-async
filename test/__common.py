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


import gc
import unittest


__all__ = ('NotifyTestCase',)



class NotifyTestCase (unittest.TestCase):

    def setUp (self):
        gc.set_threshold (0, 0, 0)
        super (NotifyTestCase, self).setUp ()


    def assert_equal_thoroughly (self, value1, value2):
        self.assert_(    value1 == value2)
        self.assert_(not value1 != value2)

        try:
            hash1 = hash (value1)
            hash2 = hash (value2)

        except TypeError:
            # It is OK, at least one value is unhashable then.
            pass

        else:
            self.assert_(hash1 == hash2)


    def assert_not_equal_thoroughly (self, value1, value2):
        self.assert_(    value1 != value2)
        self.assert_(not value1 == value2)

        # Note: hashes are _not_ required to be different, so don't test them.


    def assert_results (self, *results):
        valid_results = list (results)

        if self.results != valid_results:
            raise AssertionError ('results: %s; expected: %s' % (self.results, valid_results))


    def simple_handler (self, *arguments):
        if len (arguments) == 1:
            arguments = arguments[0]

        self.results.append (arguments)


    def collect_garbage (self, times = 1):
        for k in range (0, times):
            gc.collect ()



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
