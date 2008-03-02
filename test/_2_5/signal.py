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


# TODO: Merge this file into `test/signal.py' when Py-notify relies on Python 2.5 or
#       later.


from __future__    import with_statement

from contextlib    import nested

from notify.signal import Signal
from test.__common import NotifyTestCase, NotifyTestObject, ignoring_exceptions


__all__ = ('SignalContextManagerTestCase',)



class SignalContextManagerTestCase (NotifyTestCase):

    def test_connecting_1 (self):
        test   = NotifyTestObject ()
        signal = Signal ()

        signal.emit (1)

        with signal.connecting (test.simple_handler):
            signal.emit (2)

        signal.emit (3)

        test.assert_results (2)


    def test_connecting_2 (self):
        test   = NotifyTestObject ()
        signal = Signal ()

        signal.emit (1)

        with nested (ignoring_exceptions (), signal.connecting (test.simple_handler)):
            signal.emit (2)
            raise Exception

        signal.emit (3)

        test.assert_results (2)


    def test_connecting_safely_1 (self):
        test   = NotifyTestObject ()
        signal = Signal ()

        signal.emit (1)

        with signal.connecting_safely (test.simple_handler):
            signal.emit (2)

            with signal.connecting_safely (test.simple_handler):
                signal.emit (3)

            signal.emit (4)

        signal.emit (5)

        test.assert_results (2, 3, 4)


    def test_connecting_safely_2 (self):
        test   = NotifyTestObject ()
        signal = Signal ()

        signal.emit (1)

        with nested (ignoring_exceptions (), signal.connecting_safely (test.simple_handler)):
            signal.emit (2)
            raise Exception

        signal.emit (3)

        test.assert_results (2)


    def test_blocking_1 (self):
        test   = NotifyTestObject ()
        signal = Signal ()

        signal.connect (test.simple_handler)

        signal.emit (1)

        with signal.blocking (test.simple_handler):
            signal.emit (2)

        signal.emit (3)

        test.assert_results (1, 3)


    def test_blocking_2 (self):
        test   = NotifyTestObject ()
        signal = Signal ()

        signal.connect (test.simple_handler)

        signal.emit (1)

        with nested (ignoring_exceptions (), signal.blocking (test.simple_handler)):
            signal.emit (2)
            raise Exception

        signal.emit (3)

        test.assert_results (1, 3)



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
