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


if __name__ == '__main__':
    import os
    import sys

    sys.path.insert (0, os.path.join (sys.path[0], os.pardir))


import unittest

from notify.signal import AbstractSignal, Signal
from test.__common import NotifyTestCase, NotifyTestObject



# Note: generally, don't reuse one signal objects in several test methods.  If the signal
# fails to remove a handler, subsequent tests might fail, even though they would have run
# correctly with a fresh signal object.

class SimpleSignalTestCase (NotifyTestCase):

    def test_connect (self):
        test   = NotifyTestObject ()
        signal = Signal ()

        signal.connect (test.simple_handler)
        signal.emit ()

        self.assert_        (signal.has_handlers ())
        self.assert_        (signal)
        test.assert_results (())


    def test_connect_safe (self):
        test   = NotifyTestObject ()
        signal = Signal ()

        signal.connect_safe (test.simple_handler)
        signal.connect_safe (test.simple_handler)
        signal.emit ()

        self.assert_        (signal.has_handlers ())
        self.assert_        (signal)
        test.assert_results (())


    def test_connect_with_arguments (self):
        test   = NotifyTestObject ()
        signal = Signal ()

        signal.connect_safe (test.simple_handler, 'one argument')
        signal.connect_safe (test.simple_handler, 'first', 'second', 3)

        signal.emit ()
        signal.emit ('a', 'b')

        test.assert_results ('one argument', ('first', 'second', 3),
                             ('one argument', 'a', 'b'), ('first', 'second', 3, 'a', 'b'))


    def test_connect_with_keywords (self):
        test   = NotifyTestObject ()
        signal = Signal ()

        signal.connect_safe (test.simple_keywords_handler, a = 1)
        signal.connect_safe (test.simple_keywords_handler, a = 2, b = 3)

        signal.emit ()
        signal.emit (b = 42)
        signal.emit ('ham')

        test.assert_results ({ 'a': 1 },          { 'a': 2, 'b' : 3 },
                             # Note that emission keyword arguments must override
                             # connection-time keyword arguments.
                             { 'a': 1, 'b': 42 }, { 'a': 2, 'b' : 42 },
                             ('ham', { 'a': 1 }), ('ham', { 'a': 2, 'b' : 3 }))


    def test_argument_passing (self):
        test   = NotifyTestObject ()
        signal = Signal ()

        signal.connect (test.simple_handler)
        signal.emit (45, 'abc')

        test.assert_results ((45, 'abc'))


    def test_mixed_argument_passing (self):
        test   = NotifyTestObject ()
        signal = Signal ()

        signal.connect (test.simple_keywords_handler)
        signal.emit (ham = 'spam')
        signal.emit (42)
        signal.emit (1, 2, 3, foo = 'bar')

        test.assert_results ({ 'ham': 'spam' },
                             (42, { }),
                             (1, 2, 3, { 'foo': 'bar' }))


    def test_disconnect (self):
        test   = NotifyTestObject ()
        signal = Signal ()

        signal.connect (test.simple_handler)
        signal.emit ()

        signal.disconnect (test.simple_handler)
        signal.emit ()

        test.assert_results (())


    def test_disconnect_all (self):
        test   = NotifyTestObject ()
        signal = Signal ()

        signal.connect (test.simple_handler)
        signal.connect (test.simple_handler)
        signal.connect (test.simple_handler)
        signal.emit (1)

        signal.disconnect (test.simple_handler)
        signal.emit (2)

        signal.disconnect_all (test.simple_handler)
        signal.emit (3)

        test.assert_results (1, 1, 1, 2, 2)


    def test_connect_disconnect (self):
        test   = NotifyTestObject ()
        signal = Signal ()

        signal.connect (test.simple_handler)
        signal.connect (test.simple_handler_100)

        signal.emit (1)

        # This must be a no-op.
        signal.connect    (test.simple_handler)
        signal.disconnect (test.simple_handler)

        signal.emit (2)

        # This must be a no-op.
        signal.connect    (test.simple_handler_100)
        signal.disconnect (test.simple_handler_100)

        signal.emit (3)

        test.assert_results (1, 101, 2, 102, 3, 103)


    def test_block (self):
        test   = NotifyTestObject ()
        signal = Signal ()

        signal.connect (test.simple_handler)
        signal.emit (1)

        signal.block (test.simple_handler)
        signal.emit (2)

        test.assert_results (1)


    def test_unblock (self):
        test   = NotifyTestObject ()
        signal = Signal ()

        signal.connect (test.simple_handler)
        signal.emit (1)

        signal.block (test.simple_handler)
        signal.emit (2)

        signal.unblock (test.simple_handler)
        signal.emit (3)

        test.assert_results (1, 3)


    def test_emission_level_1 (self):
        signal = Signal (Signal.VALUE_LIST)

        self.assertEqual (signal.emission_level, 0)

        signal.connect (lambda: signal.emission_level)

        self.assertEqual (signal.emit (), [1])

        signal = Signal (Signal.VALUE_LIST)

        def stop_emission_and_get_level ():
            signal.stop_emission ()
            return signal.emission_level

        signal.connect (stop_emission_and_get_level)

        self.assertEqual (signal.emit (), [1])


    def test_emission_level_2 (self):
        test   = NotifyTestObject ()
        signal = Signal ()

        def reemit_if_shallow ():
            test.results.append (signal.emission_level)
            if signal.emission_level < 3:
                signal.emit ()

        signal.connect (reemit_if_shallow)
        signal.emit ()

        test.assert_results (1, 2, 3)


    def test_emission_stop_1 (self):
        def stop_emission ():
            signal.stop_emission ()

        test   = NotifyTestObject ()
        signal = Signal ()

        signal.connect (stop_emission)
        signal.connect (test.simple_handler)
        signal.emit    ()

        test.assert_results ()


    def test_emission_stop_2 (self):
        def reemit_signal (number):
            signal.stop_emission ()
            if number < 10:
                signal (number + 1)

        test   = NotifyTestObject ()
        signal = Signal ()

        signal.connect (test.simple_handler)
        signal.connect (reemit_signal)

        # This must never be called since emission is stopped by the previous handler.
        signal.connect (test.simple_handler)

        signal.emit (0)

        test.assert_results (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)


    def test_emission_stop_3 (self):
        def stop_emission ():
            was_stopped = signal.emission_stopped
            signal.stop_emission ()
            return was_stopped, signal.emission_stopped

        signal = Signal (Signal.VALUE_LIST)
        signal.connect (stop_emission)

        self.assertEqual (signal.emit (), [(False, True)])



class RecursiveEmissionSignalTestCase (NotifyTestCase):

    def test_recursive_invocation_1 (self):
        test = self._RecursiveTestObject (Signal ())

        test.signal.connect (test.recursive_handler)
        test.signal.emit (0)

        test.assert_results (0, 1, 2, 3, 4)


    def test_recursive_invocation_2 (self):
        test = self._RecursiveTestObject (Signal ())

        test.signal.connect (test.recursive_handler)
        test.signal.connect (test.simple_handler_100)
        test.signal.emit (0)

        test.assert_results (0, 1, 2, 3, 4,
                             104, 103, 102, 101, 100)


    def test_recursive_invocation_3 (self):
        test = self._RecursiveTestObject (Signal ())

        test.signal.connect (test.simple_handler_100)
        test.signal.connect (test.recursive_handler)
        test.signal.connect (test.simple_handler_200)
        test.signal.emit (0)

        test.assert_results (100, 0,
                             101, 1,
                             102, 2,
                             103, 3,
                             104, 4,
                             204, 203, 202, 201, 200)


    def test_connect_in_recursive_emission_1 (self):
        test = self._RecursiveTestObject (Signal ())

        test.signal.connect (test.connecting_recursive_handler)
        test.signal.emit (0)

        test.assert_results (0, 1, 2, 3, 4,
                             104, 104, 104,
                             103, 103, 103,
                             102, 102, 102,
                             101, 101, 101,
                             100, 100, 100)


    def test_connect_in_recursive_emission_2 (self):
        test = self._RecursiveTestObject (Signal ())

        test.signal.connect (test.safe_connecting_recursive_handler)
        test.signal.emit (0)

        test.assert_results (0, 1, 2, 3, 4,
                             104, 103, 102, 101, 100)


    def test_disconnect_in_recursive_emission_1 (self):
        test = self._RecursiveTestObject (Signal ())

        test.signal.connect (test.simple_handler_100)
        test.signal.connect (test.disconnecting_recursive_handler)
        test.signal.emit (0)

        test.assert_results (100, 0, 101, 1, 102, 2, 3, 4)


    def test_disconnect_in_recursive_emission_2 (self):
        test = self._RecursiveTestObject (Signal ())

        test.signal.connect (test.self_disconnecting_recursive_handler)
        test.signal.emit (0)

        test.assert_results (0, 1, 2)


    def test_block_in_recursive_emission_1 (self):
        test = self._RecursiveTestObject (Signal ())

        test.signal.connect (test.simple_handler_100)
        test.signal.connect (test.blocking_recursive_handler)
        test.signal.connect (test.simple_handler_100)
        test.signal.emit (0)

        test.assert_results (100, 0,
                             101, 1,
                             102, 2,
                             3,
                             4,
                             102, 101, 100)


    def test_block_in_recursive_emission_2 (self):
        test = self._RecursiveTestObject (Signal ())

        test.signal.connect (test.simple_handler)
        test.signal.connect (lambda x: test.signal.block (test.simple_handler))
        test.signal.connect (test.simple_handler)

        test.signal.emit (1)

        test.assert_results (1)


    def test_unblock_in_recursive_emission_1 (self):
        test = self._RecursiveTestObject (Signal ())

        test.signal.connect (test.simple_handler)
        test.signal.connect (lambda x: test.signal.unblock (test.simple_handler))
        test.signal.connect (test.simple_handler)

        test.signal.block (test.simple_handler)
        test.signal.emit (1)

        test.assert_results (1)


    def test_unblock_in_recursive_emission_2 (self):
        test = self._RecursiveTestObject (Signal ())

        test.signal.connect (test.simple_handler_100)
        test.signal.connect (test.unblocking_recursive_handler)
        test.signal.connect (test.simple_handler_100)

        test.signal.block (test.simple_handler_100)
        test.signal.block (test.simple_handler_100)

        test.signal.emit (0)

        test.assert_results (0, 1, 2, 3, 104, 4, 104, 103, 102, 101, 100)


    class _RecursiveTestObject (NotifyTestObject):

        def __init__(self, signal):
            super (RecursiveEmissionSignalTestCase._RecursiveTestObject, self).__init__()
            self.signal = signal

        def recursive_handler (self, *arguments):
            self.simple_handler (*arguments)

            if arguments[0] < 4:
                self.signal.emit (arguments[0] + 1)


        def connecting_recursive_handler (self, *arguments):
            self.simple_handler (*arguments)

            if arguments[0] >= 2:
                self.signal.connect (self.simple_handler_100)

            if arguments[0] < 4:
                self.signal.emit (arguments[0] + 1)


        def safe_connecting_recursive_handler (self, *arguments):
            self.simple_handler (*arguments)

            if arguments[0] >= 2:
                self.signal.connect_safe (self.simple_handler_100)

            if arguments[0] < 4:
                self.signal.emit (arguments[0] + 1)


        def disconnecting_recursive_handler (self, *arguments):
            self.simple_handler (*arguments)

            if arguments[0] >= 2:
                self.signal.disconnect (self.simple_handler_100)

            if arguments[0] < 4:
                self.signal.emit (arguments[0] + 1)


        def self_disconnecting_recursive_handler (self, *arguments):
            self.simple_handler (*arguments)

            if arguments[0] >= 2:
                self.signal.disconnect (self.self_disconnecting_recursive_handler)

            if arguments[0] < 4:
                self.signal.emit (arguments[0] + 1)


        def blocking_recursive_handler (self, *arguments):
            self.simple_handler (*arguments)

            if arguments[0] >= 2:
                self.signal.block (self.simple_handler_100)

            if arguments[0] < 4:
                self.signal.emit (arguments[0] + 1)

            if arguments[0] >= 2:
                self.signal.unblock (self.simple_handler_100)


        def unblocking_recursive_handler (self, *arguments):
            self.simple_handler (*arguments)

            if arguments[0] >= 2:
                self.signal.unblock (self.simple_handler_100)

            if arguments[0] < 4:
                self.signal.emit (arguments[0] + 1)



class AccumulatorSignalTestCase (NotifyTestCase):

    def test_any_accepts_accumulator (self):
        signal = Signal (AbstractSignal.ANY_ACCEPTS)
        self.assertEqual (signal.emit (), False)

        signal.connect (lambda: False)
        self.assertEqual (signal.emit (), False)

        signal.connect (lambda: ())
        self.assertEqual (signal.emit (), ())

        signal.connect (lambda: 'I accept')
        self.assertEqual (signal.emit (), 'I accept')

        signal.connect (lambda: ())
        self.assertEqual (signal.emit (), 'I accept')


    def test_all_accept_accumulator (self):
        signal = Signal (AbstractSignal.ALL_ACCEPT)
        self.assertEqual (signal.emit (), True)

        signal.connect (lambda: True)
        self.assertEqual (signal.emit (), True)

        signal.connect (lambda: 'I accept')
        self.assertEqual (signal.emit (), 'I accept')

        signal.connect (lambda: [])
        self.assertEqual (signal.emit (), [])

        signal.connect (lambda: True)
        self.assertEqual (signal.emit (), [])


    def test_last_value_accumulator (self):
        signal = Signal (AbstractSignal.LAST_VALUE)
        self.assertEqual (signal.emit (), None)

        signal.connect (lambda: 15)
        self.assertEqual (signal.emit (), 15)

        signal.connect (lambda: 'abc')
        self.assertEqual (signal.emit (), 'abc')


    def test_value_list_accumulator (self):
        signal = Signal (AbstractSignal.VALUE_LIST)
        self.assertEqual (signal.emit (), [])

        signal.connect (lambda: 50)
        self.assertEqual (signal.emit (), [50])

        signal.connect (lambda: None)
        signal.connect (lambda: ())
        self.assertEqual (signal.emit (), [50, None, ()])


    def test_custom_accumulator (self):

        class CustomAccumulator (AbstractSignal.AbstractAccumulator):

            def get_initial_value (self):
                return 10

            def accumulate_value (self, accumulated_value, value_to_add):
                return accumulated_value + value_to_add

            def should_continue (self, accumulated_value):
                return accumulated_value <= 50

            def post_process_value (self, accumulated_value):
                return -accumulated_value


        signal = Signal (CustomAccumulator ())
        self.assertEqual (signal.emit (), -10)

        signal.connect (lambda: 15)
        self.assertEqual (signal.emit (), -25)

        signal.connect (lambda: 20)
        self.assertEqual (signal.emit (), -45)

        signal.connect (lambda: 30)
        self.assertEqual (signal.emit (), -75)

        # This handler should never be invoked.
        signal.connect (lambda: 50)
        self.assertEqual (signal.emit (), -75)



# Note: we explicitly test protected field of `Signal' class, because there is nothing
# public that indicates number of garbage-collected, but not yet removed handlers.  Yet we
# want that a call to emit() does remove such handlers, so that list of signal handlers
# doesn't grow over time if implicit disconnection is used.

class HandlerGarbageCollectionTestCase (NotifyTestCase):

    class HandlerObject (object):

        def __init__(self, test):
            self.__test = test

        def simple_handler (self, *arguments):
            self.__test.simple_handler (*arguments)


    def test_handler_garbage_collection_1 (self):
        test   = NotifyTestObject ()
        signal = Signal ()

        handler = HandlerGarbageCollectionTestCase.HandlerObject (test)
        signal.connect (handler.simple_handler)

        self.assert_(signal._handlers is not None)

        signal.emit (1)

        del handler
        self.collect_garbage ()

        self.assert_(signal._handlers is not None)

        signal.emit (2)

        self.assert_(signal._handlers is None)
        test.assert_results (1)


    def test_handler_garbage_collection_2 (self):
        test   = NotifyTestObject ()
        signal = Signal ()

        handler = HandlerGarbageCollectionTestCase.HandlerObject (test)

        signal.connect (lambda *ignored: signal.stop_emission ())
        signal.connect (handler.simple_handler)

        self.assertEqual (len (signal._handlers), 2)

        signal.emit (1)

        del handler
        self.collect_garbage ()

        self.assertEqual (len (signal._handlers), 2)

        signal.emit (2)

        # Even though emission is stopped by the first handler, signal must still notice
        # that it should remove the second one.
        self.assertEqual (len (signal._handlers), 1)
        test.assert_results ()


    def test_handler_garbage_collection_3 (self):
        test   = NotifyTestObject ()
        signal = Signal (AbstractSignal.ANY_ACCEPTS)

        handler = HandlerGarbageCollectionTestCase.HandlerObject (test)

        def accepting_handler (*arguments):
            test.simple_handler_100 (*arguments)
            return arguments[0]

        signal.connect (accepting_handler)
        signal.connect (handler.simple_handler)

        self.assertEqual (len (signal._handlers), 2)

        signal.emit (1)

        del handler
        self.collect_garbage ()

        self.assertEqual (len (signal._handlers), 2)

        signal.emit (2)

        # This time emission is stopped by accumulator, but still the gc-collected handler
        # must be removed.
        self.assertEqual (len (signal._handlers), 1)
        test.assert_results (101, 102)



class ExoticSignalTestCase (NotifyTestCase):

    def test_disconnect_blocked_handler_1 (self):
        test   = NotifyTestObject ()
        signal = Signal ()

        signal.connect (test.simple_handler)
        signal.emit (1)

        signal.block (test.simple_handler)
        signal.emit (2)

        signal.disconnect (test.simple_handler)
        signal.emit (3)

        signal.connect (test.simple_handler)
        signal.emit (4)

        test.assert_results (1, 4)


    def test_disconnect_blocked_handler_2 (self):
        test   = NotifyTestObject ()
        signal = Signal ()

        signal.connect (test.simple_handler)
        signal.connect (test.simple_handler)
        signal.emit (1)

        signal.block (test.simple_handler)
        signal.emit (2)

        signal.disconnect (test.simple_handler)
        signal.emit (3)

        signal.connect (test.simple_handler)
        signal.emit (4)

        signal.unblock (test.simple_handler)
        signal.emit (5)

        test.assert_results (1, 1, 5, 5)


    def test_disconnect_blocked_handler_3 (self):
        test   = NotifyTestObject ()
        signal = Signal ()

        signal.connect (test.simple_handler)
        signal.connect (test.simple_handler)
        signal.emit (1)

        signal.block (test.simple_handler)
        signal.emit (2)

        signal.disconnect_all (test.simple_handler)
        signal.emit (3)

        signal.connect (test.simple_handler)
        signal.emit (4)

        signal.unblock (test.simple_handler)
        signal.emit (5)

        test.assert_results (1, 1, 4, 5)



import __future__

if NotifyTestCase.note_skipped_tests ('with_statement' in __future__.all_feature_names):
    from test._2_5.signal import SignalContextManagerTestCase



if __name__ == '__main__':
    unittest.main ()



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
