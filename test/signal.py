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

from notify.signal import *
from test.__common import *



# Note: generally, don't reuse one signal objects in several test methods.  If the signal
# fails to remove a handler, subsequent tests might fail, even though they would have run
# correctly with a fresh signal object.

class SimpleSignalTestCase (NotifyTestCase):

    def test_connect (self):
        signal       = Signal ()
        self.results = []

        signal.connect (self.simple_handler)
        signal.emit ()

        self.assert_        (signal.has_handlers ())
        self.assert_        (signal)
        self.assert_results (())


    def test_connect_safe (self):
        signal       = Signal ()
        self.results = []

        signal.connect_safe (self.simple_handler)
        signal.connect_safe (self.simple_handler)
        signal.emit ()

        self.assert_        (signal.has_handlers ())
        self.assert_        (signal)
        self.assert_results (())


    def test_connect_with_arguments (self):
        signal       = Signal ()
        self.results = []

        signal.connect_safe (self.simple_handler, 'one argument')
        signal.connect_safe (self.simple_handler, 'first', 'second', 3)

        signal.emit ()
        signal.emit ('a', 'b')

        self.assert_results ('one argument', ('first', 'second', 3),
                             ('one argument', 'a', 'b'), ('first', 'second', 3, 'a', 'b'))


    def test_argument_passing (self):
        signal       = Signal ()
        self.results = []

        signal.connect (self.simple_handler)
        signal.emit (45, 'abc')

        self.assert_results ((45, 'abc'))


    def test_disconnect (self):
        signal       = Signal ()
        self.results = []

        signal.connect (self.simple_handler)
        signal.emit ()

        signal.disconnect (self.simple_handler)
        signal.emit ()

        self.assert_results (())


    def test_disconnect_all (self):
        signal       = Signal ()
        self.results = []

        signal.connect (self.simple_handler)
        signal.connect (self.simple_handler)
        signal.connect (self.simple_handler)
        signal.emit (1)

        signal.disconnect (self.simple_handler)
        signal.emit (2)

        signal.disconnect_all (self.simple_handler)
        signal.emit (3)

        self.assert_results (1, 1, 1, 2, 2)


    def test_block (self):
        signal       = Signal ()
        self.results = []

        signal.connect (self.simple_handler)
        signal.emit (1)

        signal.block (self.simple_handler)
        signal.emit (2)

        self.assert_results (1)


    def test_unblock (self):
        signal       = Signal ()
        self.results = []

        signal.connect (self.simple_handler)
        signal.emit (1)

        signal.block (self.simple_handler)
        signal.emit (2)

        signal.unblock (self.simple_handler)
        signal.emit (3)

        self.assert_results (1, 3)


    def test_emission_stop_1 (self):
        def stop_emission ():
            signal.stop_emission ()

        signal       = Signal ()
        self.results = []

        signal.connect (stop_emission)
        signal.connect (self.simple_handler)
        signal.emit    ()

        self.assert_results ()


    def test_emission_stop_2 (self):
        def reemit_signal (number):
            signal.stop_emission ()
            if number < 10:
                signal (number + 1)

        signal       = Signal ()
        self.results = []

        signal.connect (self.simple_handler)
        signal.connect (reemit_signal)

        # This must never be called since emission is stopped by the previous handler.
        signal.connect (self.simple_handler)

        signal.emit (0)

        self.assert_results (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)


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
        signal       = Signal ()
        self.signal  = signal
        self.results = []

        signal.connect (self.recursive_handler)
        signal.emit (0)

        del self.signal
        self.assert_results (0, 1, 2, 3, 4)


    def test_recursive_invocation_2 (self):
        signal       = Signal ()
        self.signal  = signal
        self.results = []

        signal.connect (self.recursive_handler)
        signal.connect (self.simple_handler_100)
        signal.emit (0)

        del self.signal
        self.assert_results (0, 1, 2, 3, 4,
                             104, 103, 102, 101, 100)


    def test_recursive_invocation_3 (self):
        signal       = Signal ()
        self.signal  = signal
        self.results = []

        signal.connect (self.simple_handler_100)
        signal.connect (self.recursive_handler)
        signal.connect (self.simple_handler_200)
        signal.emit (0)

        del self.signal
        self.assert_results (100, 0,
                             101, 1,
                             102, 2,
                             103, 3,
                             104, 4,
                             204, 203, 202, 201, 200)


    def test_connect_in_recursive_emission_1 (self):
        signal       = Signal ()
        self.signal  = signal
        self.results = []

        signal.connect (self.connecting_recursive_handler)
        signal.emit (0)

        del self.signal
        self.assert_results (0, 1, 2, 3, 4,
                             104, 104, 104,
                             103, 103, 103,
                             102, 102, 102,
                             101, 101, 101,
                             100, 100, 100)


    def test_connect_in_recursive_emission_2 (self):
        signal       = Signal ()
        self.signal  = signal
        self.results = []

        signal.connect (self.safe_connecting_recursive_handler)
        signal.emit (0)

        del self.signal
        self.assert_results (0, 1, 2, 3, 4,
                             104, 103, 102, 101, 100)


    def test_disconnect_in_recursive_emission_1 (self):
        signal       = Signal ()
        self.signal  = signal
        self.results = []

        signal.connect (self.simple_handler_100)
        signal.connect (self.disconnecting_recursive_handler)
        signal.emit (0)

        del self.signal
        self.assert_results (100, 0, 101, 1, 102, 2, 3, 4)


    def test_disconnect_in_recursive_emission_2 (self):
        signal       = Signal ()
        self.signal  = signal
        self.results = []

        signal.connect (self.self_disconnecting_recursive_handler)
        signal.emit (0)

        del self.signal
        self.assert_results (0, 1, 2)


    def test_block_in_recursive_emission_1 (self):
        signal       = Signal ()
        self.signal  = signal
        self.results = []

        signal.connect (self.simple_handler_100)
        signal.connect (self.blocking_recursive_handler)
        signal.connect (self.simple_handler_100)
        signal.emit (0)

        del self.signal
        self.assert_results (100, 0,
                             101, 1,
                             102, 2,
                             3,
                             4,
                             102, 101, 100)


    def test_block_in_recursive_emission_2 (self):
        signal       = Signal ()
        self.results = []

        signal.connect (self.simple_handler)
        signal.connect (lambda x: signal.block (self.simple_handler))
        signal.connect (self.simple_handler)

        signal.emit (1)

        self.assert_results (1)


    def simple_handler_100 (self, *arguments):
        self.simple_handler (100 + arguments[0])


    def simple_handler_200 (self, *arguments):
        self.simple_handler (200 + arguments[0])


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



class ExoticSignalTestCase (NotifyTestCase):

    def test_disconnect_blocked_handler_1 (self):
        signal       = Signal ()
        self.results = []

        signal.connect (self.simple_handler)
        signal.emit (1)

        signal.block (self.simple_handler)
        signal.emit (2)

        signal.disconnect (self.simple_handler)
        signal.emit (3)

        signal.connect (self.simple_handler)
        signal.emit (4)

        self.assert_results (1, 4)


    def test_disconnect_blocked_handler_2 (self):
        signal       = Signal ()
        self.results = []

        signal.connect (self.simple_handler)
        signal.connect (self.simple_handler)
        signal.emit (1)

        signal.block (self.simple_handler)
        signal.emit (2)

        signal.disconnect (self.simple_handler)
        signal.emit (3)

        signal.connect (self.simple_handler)
        signal.emit (4)

        signal.unblock (self.simple_handler)
        signal.emit (5)

        self.assert_results (1, 1, 5, 5)


    def test_disconnect_blocked_handler_3 (self):
        signal       = Signal ()
        self.results = []

        signal.connect (self.simple_handler)
        signal.connect (self.simple_handler)
        signal.emit (1)

        signal.block (self.simple_handler)
        signal.emit (2)

        signal.disconnect_all (self.simple_handler)
        signal.emit (3)

        signal.connect (self.simple_handler)
        signal.emit (4)

        signal.unblock (self.simple_handler)
        signal.emit (5)

        self.assert_results (1, 1, 4, 5)



if __name__ == '__main__':
    unittest.main ()



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
