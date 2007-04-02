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
import weakref
import operator

from notify.condition import *
from notify.variable  import *
from test.__common    import *



class BaseConditionTestCase (NotifyTestCase):

    def test_mutable (self):
        # This also stresses usage algorithm, as a bonus.
        mutable_condition  = Condition (False)
        not_condition      = ~mutable_condition
        and_condition      = not_condition & mutable_condition
        or_condition       = and_condition | not_condition
        xor_condition      = or_condition  ^ and_condition
        if_else_condition  = or_condition.if_else (mutable_condition, or_condition)

        self.assert_(mutable_condition    .mutable)
        self.assert_(not not_condition    .mutable)
        self.assert_(not and_condition    .mutable)
        self.assert_(not or_condition     .mutable)
        self.assert_(not xor_condition    .mutable)
        self.assert_(not if_else_condition.mutable)



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


    def test_if_else (self):
        condition1 = Condition (False)
        condition2 = Condition (False)
        condition3 = Condition (False)

        if_else_condition = condition1.if_else (condition2, condition3)
        self.assertEqual (if_else_condition.state, False)

        condition1.state = False
        condition2.state = False
        condition3.state = True
        self.assertEqual (if_else_condition.state, True)

        condition1.state = False
        condition2.state = True
        condition3.state = False
        self.assertEqual (if_else_condition.state, False)

        condition1.state = False
        condition2.state = True
        condition3.state = True
        self.assertEqual (if_else_condition.state, True)

        condition1.state = True
        condition2.state = False
        condition3.state = False
        self.assertEqual (if_else_condition.state, False)

        condition1.state = True
        condition2.state = False
        condition3.state = True
        self.assertEqual (if_else_condition.state, False)

        condition1.state = True
        condition2.state = True
        condition3.state = False
        self.assertEqual (if_else_condition.state, True)

        condition1.state = True
        condition2.state = True
        condition3.state = True
        self.assertEqual (if_else_condition.state, True)



class WatcherConditionTestCase (NotifyTestCase):

    def test_watcher_condition_1 (self):
        self.results = []

        watcher = WatcherCondition ()
        watcher.store (self.simple_handler)

        condition = Condition (True)
        watcher.watch (condition)

        condition.state = False

        self.assert_results (False, True, False)


    def test_watcher_condition_2 (self):
        self.results = []

        condition1 = Condition (True)
        condition2 = Condition (False)
        condition3 = Condition (False)

        watcher = WatcherCondition (condition1)
        watcher.store (self.simple_handler)

        watcher.watch (condition2)
        watcher.watch (condition3)
        watcher.watch (None)

        # Later two watch() calls must not change watcher's state.
        self.assert_results (True, False)


    def test_watcher_condition_error_1 (self):
        self.assertRaises (TypeError, lambda: WatcherCondition (25))


    def test_watcher_condition_error_2 (self):
        watcher = WatcherCondition ()
        self.assertRaises (TypeError, lambda: watcher.watch (25))


    def test_watcher_condition_error_3 (self):
        condition = Condition (True)
        watcher   = WatcherCondition (condition)

        self.assertRaises (TypeError, lambda: watcher.watch (watcher))



class GarbageCollectionConditionTestCase (NotifyTestCase):

    def test_garbage_collection_1 (self):
        self.results = []

        variable = Variable ()

        condition = variable.is_true ()
        condition.store (self.simple_handler)
        condition = weakref.ref (condition)

        # This must not collect the `is_true' condition, even though it is not directly
        # referenced at all.
        self.collect_garbage ()
        self.assertNotEqual (condition (), None)

        self.collect_garbage ()
        variable.value = 10

        # This makes condition `unused' and it must become available to garbage collector
        # again.
        del variable
        self.collect_garbage ()

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

        self.collect_garbage ()
        self.assertNotEqual (condition1 (), None)
        self.assertNotEqual (condition2 (), None)

        self.collect_garbage ()
        variable.value = 10

        del variable

        # Run twice so that both outstanding conditions can be collected.
        self.collect_garbage (2)

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

        self.collect_garbage ()
        self.assertNotEqual (condition1 (), None)
        self.assertNotEqual (condition2 (), None)

        self.collect_garbage ()
        variable.value = 10

        condition2 ().changed.disconnect (self.simple_handler)

        # FIXME: Invent a way to calculate times that is not dependent on implementation
        #        details.
        self.collect_garbage (4)

        self.assertEqual (condition1 (), None)
        self.assertEqual (condition2 (), None)

        variable = weakref.ref (variable)
        self.collect_garbage ()

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
            self.collect_garbage (2)

            self.assertNotEqual (binary_condition (), None)

            condition2.state = True

            del condition2
            self.collect_garbage (2)

            self.assertEqual (binary_condition (), None)

            expected_results = []
            for state1, state2 in ((True, False), (True, True)):
                if not expected_results or expected_results[-1] != _operator (state1, state2):
                    expected_results.append (_operator (state1, state2))

            self.assert_results (*expected_results)


    def test_garbage_collection_if_else (self):
        self.results     = []

        condition1        = Condition (False)
        condition2        = Condition (False)
        condition3        = Condition (True)
        if_else_condition = condition1.if_else (condition2, condition3)

        if_else_condition.store (self.simple_handler)
        if_else_condition = weakref.ref (if_else_condition)

        del condition2
        self.collect_garbage (2)

        self.assertNotEqual (if_else_condition (), None)

        condition3.state = False

        del condition1
        self.collect_garbage (2)

        self.assertNotEqual (if_else_condition (), None)

        condition3.state = True

        del condition3
        self.collect_garbage (2)

        self.assertEqual    (if_else_condition (), None)
        self.assert_results (True, False, True)


    def test_garbage_collection_signal_referenced_1 (self):
        condition1   = Condition (True)
        condition2   = ~condition1
        signal       = condition2.changed

        condition2   = weakref.ref (condition2)

        self.collect_garbage ()

        self.assertNotEqual (condition2 (), None)

        del condition1
        self.collect_garbage ()

        self.assertEqual (condition2 (), None)


    def test_garbage_collection_signal_referenced_2 (self):
        condition1   = Condition (True)
        condition2   = ~condition1
        signal       = condition2.changed

        signal.connect (self.simple_handler)

        condition2   = weakref.ref (condition2)

        self.collect_garbage ()

        self.assertNotEqual (condition2 (), None)

        signal.disconnect (self.simple_handler)

        self.collect_garbage ()

        self.assertNotEqual (condition2 (), None)

        del signal
        self.collect_garbage (2)

        self.assertEqual (condition2 (), None)


    def test_signal_garbage_collection (self):
        self.results = []

        condition1   = Condition (True)
        condition2   = ~condition1

        condition2.changed.connect (self.simple_handler)

        # We also assume that `Not's condition signal can be weakly referenced, but I
        # don't see other way...
        signal = weakref.ref (condition2.changed)

        condition1.state = False
        self.assert_results (True)

        condition1 = weakref.ref (condition1)
        condition2 = weakref.ref (condition2)

        self.collect_garbage (2)

        self.assertEqual (condition1 (), None)
        self.assertEqual (condition2 (), None)
        self.assertEqual (signal     (), None)



class SignalConditionTestCase (NotifyTestCase):

    def test_referenced_signal (self):
        self.results = []

        condition = Condition (False)
        signal    = (~condition).changed
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
