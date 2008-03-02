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

from notify.base      import AbstractValueObject
from notify.condition import Condition
from notify.variable  import AbstractVariable, Variable
from test.__common    import NotifyTestCase, NotifyTestObject



# Note: since base class (AbstractValueObject) is abstract, we actually test variables and
# conditions.  However, tested functionality comes from the base class.

class BaseInternalsTestCase (NotifyTestCase):

    # A half-hearted attempt to test internal `__flags' slot of `AbstractValueObject'
    # class.  We do several things that change it and test that `changed' signal is still
    # emitted fine.
    def test_internals_1 (self):
        test = NotifyTestObject ()

        condition     = Condition (False)
        not_condition = ~condition

        self.assert_(not not_condition._has_signal ())

        not_condition.changed.connect (test.simple_handler)
        self.assert_(not_condition._has_signal ())

        def set_state_true ():
            condition.state = True

        condition.with_changes_frozen (set_state_true)

        condition.state = False

        not_condition.changed.disconnect (test.simple_handler)
        self.collect_garbage ()
        self.assert_(not not_condition._has_signal ())

        not_condition.changed.connect (test.simple_handler)
        self.assert_(not_condition._has_signal ())

        condition.state = True

        test.assert_results (False, True, False)



class BaseWithChangesFrozenTestCase (NotifyTestCase):

    def test_with_changes_frozen_1 (self):
        test     = NotifyTestObject ()
        variable = Variable ()

        variable.changed.connect (test.simple_handler)
        variable.with_changes_frozen (lambda: None)

        # Must not emit `changed' signal: no changes at all.
        test.assert_results ()


    def test_with_changes_frozen_2 (self):
        test     = NotifyTestObject ()
        variable = Variable ()

        variable.changed.connect (test.simple_handler)

        def do_changes ():
            variable.value = 1

        variable.with_changes_frozen (do_changes)

        test.assert_results (1)


    def test_with_changes_frozen_3 (self):
        test     = NotifyTestObject ()
        variable = Variable ()

        variable.changed.connect (test.simple_handler)

        def do_changes ():
            variable.value = 1
            variable.value = 2

        variable.with_changes_frozen (do_changes)

        test.assert_results (2)


    def test_with_changes_frozen_4 (self):
        test     = NotifyTestObject ()
        variable = Variable ()

        variable.changed.connect (test.simple_handler)

        def do_changes ():
            variable.value = 1
            variable.value = None

        variable.with_changes_frozen (do_changes)

        # Must not emit: value returned to original.
        test.assert_results ()


    def test_with_changes_frozen_5 (self):
        test     = NotifyTestObject ()
        variable = Variable ()

        variable.changed.connect (test.simple_handler)

        def do_changes_1 ():
            variable.value = 1

            def do_changes_2 ():
                variable.value = 2

            variable.with_changes_frozen (do_changes_2)

        variable.with_changes_frozen (do_changes_1)

        test.assert_results (2)


    def test_with_changes_frozen_6 (self):
        test     = NotifyTestObject ()
        variable = Variable ()

        variable.changed.connect (test.simple_handler)

        def do_changes_1 ():
            def do_changes_2 ():
                variable.value = 1

            variable.with_changes_frozen (do_changes_2)

            variable.value = 2

        variable.with_changes_frozen (do_changes_1)

        test.assert_results (2)


    def test_with_changes_frozen_7 (self):
        test     = NotifyTestObject ()
        variable = Variable ()

        variable.changed.connect (test.simple_handler)

        def do_changes_1 ():
            def do_changes_2 ():
                variable.value = 1

            variable.with_changes_frozen (do_changes_2)

            variable.value = None

        variable.with_changes_frozen (do_changes_1)

        # Must not emit: value returned to original.
        test.assert_results ()


    def test_with_derived_variable_changes_frozen_1 (self):
        DerivedVariable = AbstractVariable.derive_type ('DerivedVariable',
                                                        getter = lambda variable: values['x'])
        test            = NotifyTestObject ()
        values          = { 'x': 1 }
        variable        = DerivedVariable ()

        variable.store (test.simple_handler)

        def do_changes (values):
            values['x'] = 2

        variable.with_changes_frozen (do_changes, values)

        # Though we never call _value_changed(), with_changes_frozen() promises to call it
        # itself in such cases.
        test.assert_results (1, 2)



class BaseDerivationTestCase (NotifyTestCase):

    def test_derivation_slots (self):
        DerivedType = AbstractValueObject.derive_type ('DerivedType')
        self.assertRaises (AttributeError, self.non_existing_attribute_setter (DerivedType ()))


    def test_derivation_dict_1 (self):
        DerivedType1 = AbstractValueObject.derive_type ('DerivedType1', dict = True)
        DerivedType1 ().this_attribute_isnt_declared_but_there_is_a_dict = None


    def test_derivation_dict_2 (self):
        # Test that derivation mechanism gracefully ignores second `dict'.
        DerivedType2 = (AbstractValueObject
                        .derive_type ('DerivedType1', dict = True)
                        .derive_type ('DerivedType2', dict = True))
        DerivedType2 ().this_attribute_isnt_declared_but_there_is_a_dict = None


    def test_derivation_dict_3 (self):
        # But test it notices there is a dict already over intermediate type.
        DerivedType3 = (AbstractValueObject
                        .derive_type ('DerivedType1', dict = True)
                        .derive_type ('DerivedType2')
                        .derive_type ('DerivedType3', dict = True))
        DerivedType3 ().this_attribute_isnt_declared_but_there_is_a_dict = None


    def test_derivation_dict_4 (self):
        class DerivedType1 (AbstractValueObject):
            pass

        # Test it notices there is a dict already in a no-slots intermediate type.
        DerivedType2 = DerivedType1.derive_type ('DerivedType2', dict = True)
        DerivedType2 ().this_attribute_isnt_declared_but_there_is_a_dict = None


    def test_derivation_module (self):
        self.assertEqual (Condition.derive_type ('Test').__module__, type (self).__module__)



import __future__

if NotifyTestCase.note_skipped_tests ('with_statement' in __future__.all_feature_names):
    from test._2_5.base import BaseContextManagerTestCase, BaseChangesFrozenContextManagerTestCase



if __name__ == '__main__':
    unittest.main ()



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
