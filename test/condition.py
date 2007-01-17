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


if __name__ == '__main__':
    import os
    import sys

    sys.path.insert (0, os.path.join (sys.path[0], os.pardir))


import unittest
import gc
import weakref
import operator

from notify.condition import *
from notify.variable  import *
from test.__common    import *



gc.set_threshold (0, 0, 0)


class BaseConditionTestCase (NotifyTestCase):

    def test_mutable (self):
        condition1 = Condition (False)
        condition2 = ~condition1

        self.assert_(condition1.mutable)
        self.assert_(not condition2.mutable)



class LogicConditionTestCase (NotifyTestCase):

    def test_not (self):
        condition = Condition (False)

        not_condition = ~condition
        self.assertEqual (not_condition.state, True)

        condition.state = True
        self.assertEqual (not_condition.state, False)


    def test_and (self):
        condition1 = Condition (False)
        condition2 = Condition (False)

        and_condition = condition1 & condition2
        self.assertEqual (and_condition.state, False)

        condition1.state = True
        condition2.state = False
        self.assertEqual (and_condition.state, False)

        condition1.state = False
        condition2.state = True
        self.assertEqual (and_condition.state, False)

        condition1.state = True
        condition2.state = True
        self.assertEqual (and_condition.state, True)


    def test_or (self):
        condition1 = Condition (False)
        condition2 = Condition (False)

        or_condition = condition1 | condition2
        self.assertEqual (or_condition.state, False)

        condition1.state = True
        condition2.state = False
        self.assertEqual (or_condition.state, True)

        condition1.state = False
        condition2.state = True
        self.assertEqual (or_condition.state, True)

        condition1.state = True
        condition2.state = True
        self.assertEqual (or_condition.state, True)


    def test_xor (self):
        condition1 = Condition (False)
        condition2 = Condition (False)

        xor_condition = condition1 ^ condition2
        self.assertEqual (xor_condition.state, False)

        condition1.state = True
        condition2.state = False
        self.assertEqual (xor_condition.state, True)

        condition1.state = False
        condition2.state = True
        self.assertEqual (xor_condition.state, True)

        condition1.state = True
        condition2.state = True
        self.assertEqual (xor_condition.state, False)


    def test_ifelse (self):
        condition1 = Condition (False)
        condition2 = Condition (False)
        condition3 = Condition (False)

        ifelse_condition = condition1.ifelse (condition2, condition3)
        self.assertEqual (ifelse_condition.state, False)

        condition1.state = False
        condition2.state = False
        condition3.state = True
        self.assertEqual (ifelse_condition.state, True)

        condition1.state = False
        condition2.state = True
        condition3.state = False
        self.assertEqual (ifelse_condition.state, False)

        condition1.state = False
        condition2.state = True
        condition3.state = True
        self.assertEqual (ifelse_condition.state, True)

        condition1.state = True
        condition2.state = False
        condition3.state = False
        self.assertEqual (ifelse_condition.state, False)

        condition1.state = True
        condition2.state = False
        condition3.state = True
        self.assertEqual (ifelse_condition.state, False)

        condition1.state = True
        condition2.state = True
        condition3.state = False
        self.assertEqual (ifelse_condition.state, True)

        condition1.state = True
        condition2.state = True
        condition3.state = True
        self.assertEqual (ifelse_condition.state, True)



class GarbageCollectionConditionTestCase (NotifyTestCase):

    def test_garbage_collection_1 (self):
        self.results = []

        variable = Variable ()

        condition = variable.is_true ()
        condition.store (self.simple_handler)
        condition = weakref.ref (condition)

        # This must not collect the `is_true' condition, even though it is not directly
        # referenced at all.
        gc.collect ()
        self.assertNotEqual (condition (), None)

        gc.collect ()
        variable.value = 10

        # This makes condition `unused' and it must become available to garbage collector
        # again.
        del variable
        gc.collect ()

        self.assertEqual (condition (), None)
        self.assert_results (False, True)


    # Same as the previous test, but with longer condition chain.
    def test_garbage_collection_2 (self):
        self.results = []

        variable = Variable ()

        condition1 = variable.is_true ()
        condition2 = ~condition1
        condition2.store (self.simple_handler)

        condition1 = weakref.ref (condition1)
        condition2 = weakref.ref (condition2)

        gc.collect ()
        self.assertNotEqual (condition1 (), None)
        self.assertNotEqual (condition2 (), None)

        gc.collect ()
        variable.value = 10

        del variable

        # Run twice so that both outstanding conditions can be collected.
        gc.collect ()
        gc.collect ()

        self.assertEqual (condition1 (), None)
        self.assertEqual (condition2 (), None)
        self.assert_results (True, False)


    # Again same as the previous test, but this time usage chain is broken from the other
    # end.
    def test_garbage_collection_3 (self):
        self.results = []

        variable = Variable ()

        condition1 = variable.is_true ()
        condition2 = ~condition1
        condition2.store (self.simple_handler)

        condition1 = weakref.ref (condition1)
        condition2 = weakref.ref (condition2)

        gc.collect ()
        self.assertNotEqual (condition1 (), None)
        self.assertNotEqual (condition2 (), None)

        gc.collect ()
        variable.value = 10

        condition2 ().signal_changed ().disconnect (self.simple_handler)

        # Run twice so that both outstanding conditions can be collected.
        gc.collect ()
        gc.collect ()

        self.assertEqual (condition1 (), None)
        self.assertEqual (condition2 (), None)

        variable = weakref.ref (variable)
        gc.collect ()

        self.assertEqual (variable (), None)

        self.assert_results (True, False)


    def test_garbage_collection_binary (self):
        for _operator in (operator.__and__, operator.__or__, operator.__xor__):
            self.results = []

            condition1       = Condition (True)
            condition2       = Condition (False)
            binary_condition = _operator (condition1, condition2)

            binary_condition.store (self.simple_handler)
            binary_condition = weakref.ref (binary_condition)

            del condition1
            gc.collect ()
            gc.collect ()

            self.assertNotEqual (binary_condition (), None)

            condition2.state = True

            del condition2
            gc.collect ()
            gc.collect ()

            self.assertEqual (binary_condition (), None)

            expected_results = []
            for state1, state2 in ((True, False), (True, True)):
                if not expected_results or expected_results[-1] != _operator (state1, state2):
                    expected_results.append (_operator (state1, state2))

            self.assert_results (*expected_results)


    def test_garbage_collection_ifelse (self):
        self.results     = []

        condition1       = Condition (False)
        condition2       = Condition (False)
        condition3       = Condition (True)
        ifelse_condition = condition1.ifelse (condition2, condition3)

        ifelse_condition.store (self.simple_handler)
        ifelse_condition = weakref.ref (ifelse_condition)

        del condition2
        gc.collect ()
        gc.collect ()

        self.assertNotEqual (ifelse_condition (), None)

        condition3.state = False

        del condition1
        gc.collect ()
        gc.collect ()

        self.assertNotEqual (ifelse_condition (), None)

        condition3.state = True

        del condition3
        gc.collect ()
        gc.collect ()

        self.assertEqual    (ifelse_condition (), None)
        self.assert_results (True, False, True)



class SignalConditionTestCase (NotifyTestCase):

    def test_referenced_signal (self):
        self.results = []

        condition = Condition (False)
        signal    = (~condition).signal_changed ()
        signal.connect (self.simple_handler)

        condition.state = True

        # This must not change anything.  But current (at the time of test addition)
        # implementation destroys the `not' condition despite the reference to its signal.
        signal.disconnect (self.simple_handler)
        signal.connect    (self.simple_handler)

        condition.state = False

        self.assert_results (False, True)



if __name__ == '__main__':
    unittest.main ()



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
