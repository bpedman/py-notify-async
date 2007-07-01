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

from notify.variable import AbstractVariable, Variable
from test.__common   import NotifyTestCase



# Note: since base class (AbstractValueObject) is abstract, we actually test variables.
# However, tested functionality comes from the base class.

class BaseWithChangesFrozenTestCase (NotifyTestCase):

    def test_with_changes_frozen_1 (self):
        variable     = Variable ()
        self.results = []

        variable.changed.connect (self.simple_handler)
        variable.with_changes_frozen (lambda: None)

        # Must not emit `changed' signal: no changes at all.
        self.assert_results ()


    def test_with_changes_frozen_2 (self):
        variable     = Variable ()
        self.results = []

        variable.changed.connect (self.simple_handler)

        def do_changes ():
            variable.value = 1

        variable.with_changes_frozen (do_changes)

        self.assert_results (1)


    def test_with_changes_frozen_3 (self):
        variable     = Variable ()
        self.results = []

        variable.changed.connect (self.simple_handler)

        def do_changes ():
            variable.value = 1
            variable.value = 2

        variable.with_changes_frozen (do_changes)

        self.assert_results (2)


    def test_with_changes_frozen_4 (self):
        variable     = Variable ()
        self.results = []

        variable.changed.connect (self.simple_handler)

        def do_changes ():
            variable.value = 1
            variable.value = None

        variable.with_changes_frozen (do_changes)

        # Must not emit: value returned to original.
        self.assert_results ()


    def test_with_changes_frozen_5 (self):
        variable     = Variable ()
        self.results = []

        variable.changed.connect (self.simple_handler)

        def do_changes_1 ():
            variable.value = 1

            def do_changes_2 ():
                variable.value = 2

            variable.with_changes_frozen (do_changes_2)

        variable.with_changes_frozen (do_changes_1)

        self.assert_results (2)


    def test_with_changes_frozen_6 (self):
        variable     = Variable ()
        self.results = []

        variable.changed.connect (self.simple_handler)

        def do_changes_1 ():
            def do_changes_2 ():
                variable.value = 1

            variable.with_changes_frozen (do_changes_2)

            variable.value = 2

        variable.with_changes_frozen (do_changes_1)

        self.assert_results (2)


    def test_with_changes_frozen_7 (self):
        variable     = Variable ()
        self.results = []

        variable.changed.connect (self.simple_handler)

        def do_changes_1 ():
            def do_changes_2 ():
                variable.value = 1

            variable.with_changes_frozen (do_changes_2)

            variable.value = None

        variable.with_changes_frozen (do_changes_1)

        # Must not emit: value returned to original.
        self.assert_results ()


    def test_with_derived_variable_changes_frozen_1 (self):
        DerivedVariable = AbstractVariable.derive_type ('DerivedVariable',
                                                        getter = lambda variable: values['x'])
        values       = { 'x': 1 }
        variable     = DerivedVariable ()
        self.results = []

        variable.store (self.simple_handler)

        def do_changes (values):
            values['x'] = 2

        variable.with_changes_frozen (do_changes, values)

        # Though we never call _value_changed(), with_changes_frozen() promises to call it
        # itself in such cases.
        self.assert_results (1, 2)



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
