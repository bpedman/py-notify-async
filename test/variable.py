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


import math
import unittest

from notify.variable import AbstractVariable, AbstractValueTrackingVariable, Variable, \
                            WatcherVariable
from notify.utils    import StringType
from test.__common   import NotifyTestCase, NotifyTestObject



class BaseVariableTestCase (NotifyTestCase):

    def test_mutable (self):
        mutable_variable = Variable ()

        self.assert_(mutable_variable.mutable)


    def test_predicate_1 (self):
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


    def test_predicate_2 (self):
        test = NotifyTestObject ()

        variable = Variable (0)
        variable.predicate (lambda value: 0 <= value < 10).store (test.simple_handler)

        variable.value = 5
        variable.value = 15
        variable.value = -1
        variable.value = 9
        variable.value = 3

        test.assert_results (True, False, True)


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


    def test_transformation_1 (self):
        variable = Variable (0)
        floor    = variable.transform (math.floor)

        self.assertEqual (floor.value, 0)
        self.assert_(not floor.mutable)

        variable.value = 10.5
        self.assertEqual (floor.value, 10)

        variable.value = 15
        self.assertEqual (floor.value, 15)


    def test_transformation_2 (self):
        test = NotifyTestObject ()

        variable = Variable (0)
        variable.transform (math.floor).store (test.simple_handler)

        variable.value = 5
        variable.value = 5.6
        variable.value = 15.7
        variable.value = 16
        variable.value = 16.5
        variable.value = 16.2

        test.assert_results (0, 5, 15, 16)


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
        test = NotifyTestObject ()

        watcher = WatcherVariable ()
        watcher.store (test.simple_handler)

        variable = Variable ('abc')
        watcher.watch (variable)

        self.assert_(watcher.watched_variable is variable)

        variable.value = 60

        test.assert_results (None, 'abc', 60)


    def test_watcher_variable_2 (self):
        test = NotifyTestObject ()

        variable1 = Variable ([])
        variable2 = Variable ('string')
        variable3 = Variable ('string')

        watcher = WatcherVariable (variable1)
        watcher.store (test.simple_handler)

        watcher.watch (variable2)
        watcher.watch (variable3)
        watcher.watch (None)

        self.assert_(watcher.watched_variable is None)

        # Later two watch() calls must not change watcher's value.
        test.assert_results ([], 'string', None)


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


    def test_derivation_6 (self):
        StringVariable = Variable.derive_type ('StringVariable',
                                               allowed_value_types = StringType,
                                               setter = lambda variable, value: None)

        variable = StringVariable ('')
        self.assertRaises (ValueError, lambda: variable.set (None))


    def test_derivation_7 (self):
        DerivedVariable = \
            AbstractValueTrackingVariable.derive_type ('DerivedVariable',
                                                       setter = lambda variable, value: None)

        variable = DerivedVariable ()
        self.assert_(variable.value is None)

        variable.set (100)
        self.assert_(variable.value == 100)

        variable.value = 'abc'
        self.assert_(variable.value == 'abc')


    def test_derivation_8 (self):
        test = NotifyTestObject ()

        DerivedVariable = \
            AbstractValueTrackingVariable.derive_type ('DerivedVariable',
                                                       getter = lambda variable: None,
                                                       setter = (lambda variable, value:
                                                                     test.simple_handler (value)))

        variable = DerivedVariable ()
        variable.set (100)
        variable.value = 'abc'

        # The default value is retrieved with the getter function, so the setter must not
        # be called during variable creation.
        test.assert_results (100, 'abc')


    def test_derivation_9 (self):
        test = NotifyTestObject ()

        DerivedVariable = \
            AbstractValueTrackingVariable.derive_type ('DerivedVariable',
                                                       setter = (lambda variable, value:
                                                                     test.simple_handler (value)))

        variable = DerivedVariable ()
        variable.set (100)
        variable.value = 'abc'

        # There is no getter at all, so setter must be called during variable creation.
        test.assert_results (None, 100, 'abc')


    def test_derivation_10 (self):
        def set_value (list, value):
            list[0] = value

        DerivedVariable = AbstractVariable.derive_type ('DerivedVariable',
                                                        object = '__list', property = 'list',
                                                        getter = lambda list: list[0],
                                                        setter = set_value)

        a = DerivedVariable ([123])

        self.assertEqual (a.value, 123)

        a.value = 'foo'

        self.assertEqual (a.value, 'foo')
        self.assertEqual (a.list,  ['foo'])


    def test_derivation_11 (self):
        # Test that derivation with keyword slot or property raises.
        self.assertRaises (ValueError, lambda: AbstractVariable.derive_type ('DerivedVariable',
                                                                             object = 'or'))
        self.assertRaises (ValueError, lambda: AbstractVariable.derive_type ('DerivedVariable',
                                                                             object   = '__class',
                                                                             property = 'class'))


    # Test against a real bug present up to 0.1.12.
    def test_derivation_12 (self):
        DerivedVariable = AbstractValueTrackingVariable.derive_type ('DerivedVariable',
                                                                     object = '__list',
                                                                     property = 'list')

        variable = DerivedVariable ([1, 2, 3], 200)
        self.assertEqual (variable.list,  [1, 2, 3])
        self.assertEqual (variable.value, 200)


    def test_object_derivation_1 (self):
        class MainObject (object):
            def __init__(self, x):
                self.__x = x

            def get_x (self):
                return self.__x

        XVariable = AbstractValueTrackingVariable.derive_type ('XVariable', object = 'main',
                                                               getter = MainObject.get_x)

        main     = MainObject (100)
        variable = XVariable (main)

        self.assert_(variable.main  is main)
        self.assert_(variable.value is main.get_x ())

        main.x = 200
        self.assert_(variable.value is main.get_x ())


    def test_object_derivation_2 (self):
        class MainObject (object):
            def __init__(self, x):
                self.__x          = x
                self.__x_variable = XVariable (self)

            def get_x (self):
                return self.__x

            def _set_x (self, x):
                self.__x = x

            x = property (lambda self: self.__x_variable)

        XVariable = AbstractValueTrackingVariable.derive_type ('XVariable',
                                                               object   = '__main',
                                                               property = 'main',
                                                               getter   = MainObject.get_x,
                                                               setter   = MainObject._set_x)

        main = MainObject (100)

        self.assert_(main.x.main  is main)
        self.assert_(main.x.value is main.get_x ())

        main.x.value = 200
        self.assert_(main.x.value is main.get_x ())

        def set_main_x ():
            main.x = None

        self.assertRaises (AttributeError, set_main_x)



    def test_derivation_slots (self):
        DerivedVariable = AbstractVariable.derive_type ('DerivedVariable')
        self.assertRaises (AttributeError, self.non_existing_attribute_setter (DerivedVariable ()))

        DerivedVariable = AbstractValueTrackingVariable.derive_type ('DerivedVariable')
        self.assertRaises (AttributeError, self.non_existing_attribute_setter (DerivedVariable ()))

        DerivedVariable = Variable.derive_type ('DerivedVariable')
        self.assertRaises (AttributeError, self.non_existing_attribute_setter (DerivedVariable ()))


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
