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

from notify.variable  import *
from test.__common    import *



class BaseVariableTestCase (NotifyTestCase):

    def test_mutable (self):
        mutable_variable = Variable ()

        self.assert_(mutable_variable.mutable)


    def test_predicate (self):
        variable        = Variable (0)
        is_single_digit = variable.predicate (lambda value: 0 <= value < 10)

        self.assert_(is_single_digit)
        self.assert_(not is_single_digit.mutable)

        variable.value = -5
        self.assert_(not is_single_digit)

        variable.value = 9
        self.assert_(is_single_digit)

        variable.value = 100
        self.assert_(not is_single_digit)


    def test_is_true (self):
        variable = Variable (0)
        is_true  = variable.is_true ()

        self.assert_(not is_true)

        variable.value = 'string'
        self.assert_(is_true)

        variable.value = []
        self.assert_(not is_true)

        variable.value = None
        self.assert_(not is_true)

        variable.value = 25
        self.assert_(is_true)


    def test_is_allowed_value (self):

        class PositiveVariable (Variable):

            def is_allowed_value (self, value):
                return isinstance (value, int) and value > 0


        variable = PositiveVariable (6)

        # Must not raise.
        variable.value = 9
        variable.value = 999

        # Must raise.
        self.assertRaises (ValueError, lambda: variable.set (0))
        self.assertRaises (ValueError, lambda: variable.set (-5))
        self.assertRaises (ValueError, lambda: variable.set (2.2))
        self.assertRaises (ValueError, lambda: variable.set ([]))



class WatcherVariableTestCase (NotifyTestCase):

    def test_watcher_variable_1 (self):
        self.results = []

        watcher = WatcherVariable ()
        watcher.store (self.simple_handler)

        variable = Variable ('abc')
        watcher.watch (variable)

        self.assert_(watcher.watched_variable is variable)

        variable.value = 60

        self.assert_results (None, 'abc', 60)


    def test_watcher_variable_2 (self):
        self.results = []

        variable1 = Variable ([])
        variable2 = Variable ('string')
        variable3 = Variable ('string')

        watcher = WatcherVariable (variable1)
        watcher.store (self.simple_handler)

        watcher.watch (variable2)
        watcher.watch (variable3)
        watcher.watch (None)

        self.assert_(watcher.watched_variable is None)

        # Later two watch() calls must not change watcher's value.
        self.assert_results ([], 'string', None)


    def test_watcher_variable_error_1 (self):
        self.assertRaises (TypeError, lambda: WatcherVariable (25))


    def test_watcher_variable_error_2 (self):
        watcher = WatcherVariable ()
        self.assertRaises (TypeError, lambda: watcher.watch (25))


    def test_watcher_variable_error_3 (self):
        variable = Variable ()
        watcher  = WatcherVariable (variable)

        self.assertRaises (ValueError, lambda: watcher.watch (watcher))
        self.assert_      (watcher.watched_variable is variable)



class VariableDerivationTestCase (NotifyTestCase):

    def test_derivation_1 (self):
        IntVariable = Variable.derive_type ('IntVariable', allowed_value_types = int)

        # Since None is not an allowed value, there must be no default constructor.
        self.assertRaises (TypeError, lambda: IntVariable ())

        count = IntVariable (10)
        self.assertEqual (count.value, 10)
        self.assertEqual (count.mutable, True)

        count.value = 30
        self.assertEqual (count.value, 30)

        self.assertRaises (ValueError, lambda: count.set ('invalid'))


    def test_derivation_2 (self):
        EnumVariable = Variable.derive_type ('EnumVariable',
                                             allowed_values = (None, 'a', 'b', 'c'))

        variable = EnumVariable ()
        self.assertEqual (variable.value, None)
        self.assertEqual (variable.mutable, True)

        variable.value = 'b'
        self.assertEqual (variable.value, 'b')

        self.assertRaises (ValueError, lambda: variable.set (15))
        self.assertRaises (ValueError, lambda: variable.set ('d'))


    def test_derivation_3 (self):
        AbstractIntVariable = AbstractValueTrackingVariable.derive_type (
            'AbstractIntVariable', allowed_value_types = int)

        self.assertEqual (AbstractIntVariable (-5).mutable, False)


    def test_derivation_4 (self):
        NumericVariable = Variable.derive_type ('NumericVariable',
                                                allowed_value_types = (int, float, complex))

        self.assertRaises (TypeError, lambda: NumericVariable ())

        variable = NumericVariable (0)

        variable.value = 15
        self.assertEqual (variable.value, 15)

        variable.value = -2.5
        self.assertEqual (variable.value, -2.5)

        variable.value = 1j
        self.assertEqual (variable.value, 1j)

        self.assertRaises (ValueError, lambda: variable.set ('string'))
        self.assertRaises (ValueError, lambda: variable.set ([]))


    def test_derivation_5 (self):
        IntVariable = Variable.derive_type ('IntVariable',
                                            allowed_value_types = int, default_value = 10)

        variable = IntVariable ()
        self.assertEqual (variable.value, 10)

        variable = IntVariable (30)
        self.assertEqual (variable.value, 30)

        self.assertRaises (ValueError, lambda: variable.set ('string'))


    def test_multiple_derivation (self):
        # Derive two types and make sure they don't spoil each other's is_allowed_value()
        # method.

        IntVariable = Variable.derive_type ('IntVariable', allowed_value_types = int)
        StrVariable = Variable.derive_type ('StrVariable', allowed_value_types = str)

        integer = IntVariable (10)
        string  = StrVariable ('test')

        integer.value = 20
        self.assertEqual (integer.value, 20)

        string.value = 'string'
        self.assertEqual (string.value, 'string')

        self.assertRaises (ValueError, lambda: integer.set ('foo'))
        self.assertRaises (ValueError, lambda: string .set (-1000))
        self.assertRaises (ValueError, lambda: integer.set (''))
        self.assertRaises (ValueError, lambda: string .set (0))



if __name__ == '__main__':
    unittest.main ()



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
