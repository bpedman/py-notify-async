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


# TODO: Merge this file into `test/base.py' when Py-notify relies on Python 2.5 or later.


from __future__      import with_statement

from contextlib      import nested

from notify.variable import AbstractVariable, Variable
from test.__common   import NotifyTestCase, ignoring_exceptions


__all__ = ('BaseContextManagerTestCase', 'BaseChangesFrozenContextManagerTestCase')



class BaseContextManagerTestCase (NotifyTestCase):

    def test_storing_1 (self):
        variable       = Variable ()
        self.results   = []

        variable.value = 100

        with variable.storing (self.simple_handler):
            variable.value = 200

        variable.value = 300

        self.assert_results (100, 200)


    def test_storing_2 (self):
        variable       = Variable ()
        self.results   = []

        variable.value = 100

        with nested (ignoring_exceptions (), variable.storing (self.simple_handler)):
            variable.value = 200
            raise Exception

        variable.value = 300

        self.assert_results (100, 200)


    def test_storing_safely_1 (self):
        variable       = Variable ()
        self.results   = []

        variable.value = 100

        with variable.storing_safely (self.simple_handler):
            variable.value = 200

            with variable.storing_safely (self.simple_handler):
                variable.value = 300

            variable.value = 400

        variable.value = 500

        self.assert_results (100, 200, 300, 400)


    def test_storing_safely_2 (self):
        variable       = Variable ()
        self.results   = []

        variable.value = 100

        with nested (ignoring_exceptions (), variable.storing_safely (self.simple_handler)):
            variable.value = 200

            with nested (ignoring_exceptions (), variable.storing_safely (self.simple_handler)):
                variable.value = 300

            variable.value = 400
            raise Exception

        variable.value = 500

        self.assert_results (100, 200, 300, 400)


    def test_synchronizing_1 (self):
        variable1       = Variable ()
        variable2       = Variable ()
        self.results    = []

        variable1.value = 100
        variable2.value = 200

        variable1.changed.connect (self.simple_handler)

        with variable1.synchronizing (variable2):
            variable2.value = 300

        variable2.value = 400

        self.assert_results (200, 300)


    def test_synchronizing_2 (self):
        variable1       = Variable ()
        variable2       = Variable ()
        self.results    = []

        variable1.value = 100
        variable2.value = 200

        variable1.changed.connect (self.simple_handler)

        with nested (ignoring_exceptions (), variable1.synchronizing (variable2)):
            variable2.value = 300
            raise Exception

        variable2.value = 400

        self.assert_results (200, 300)


    def test_synchronizing_safely_1 (self):
        variable1       = Variable ()
        variable2       = Variable ()
        self.results    = []

        variable1.value = 100
        variable2.value = 200

        variable1.changed.connect (self.simple_handler)

        variable1.synchronize (variable2)

        with variable1.synchronizing_safely (variable2):
            variable2.value = 300

        variable2.value = 400

        self.assert_results (200, 300, 400)


    def test_synchronizing_safely_2 (self):
        variable1       = Variable ()
        variable2       = Variable ()
        self.results    = []

        variable1.value = 100
        variable2.value = 200

        variable1.changed.connect (self.simple_handler)

        variable1.synchronize (variable2)

        with nested (ignoring_exceptions (), variable1.synchronizing_safely (variable2)):
            variable2.value = 300
            raise Exception

        variable2.value = 400

        self.assert_results (200, 300, 400)



class BaseChangesFrozenContextManagerTestCase (NotifyTestCase):

    def test_changes_frozen_1 (self):
        variable     = Variable ()
        self.results = []

        variable.changed.connect (self.simple_handler)

        with variable.changes_frozen ():
            pass

        # Must not emit `changed' signal: no changes at all.
        self.assert_results ()


    def test_changes_frozen_2 (self):
        variable     = Variable ()
        self.results = []

        variable.changed.connect (self.simple_handler)

        with variable.changes_frozen ():
            variable.value = 1

        self.assert_results (1)


    def test_changes_frozen_3 (self):
        variable     = Variable ()
        self.results = []

        variable.changed.connect (self.simple_handler)

        with variable.changes_frozen ():
            variable.value = 1
            variable.value = 2

        self.assert_results (2)


    def test_changes_frozen_4 (self):
        variable     = Variable ()
        self.results = []

        variable.changed.connect (self.simple_handler)

        with variable.changes_frozen ():
            variable.value = 1
            variable.value = None

        # Must not emit: value returned to original.
        self.assert_results ()


    def test_changes_frozen_5 (self):
        variable     = Variable ()
        self.results = []

        variable.changed.connect (self.simple_handler)

        with variable.changes_frozen ():
            variable.value = 1
            with variable.changes_frozen ():
                variable.value = 2

        self.assert_results (2)


    def test_changes_frozen_6 (self):
        variable     = Variable ()
        self.results = []

        variable.changed.connect (self.simple_handler)

        with variable.changes_frozen ():
            with variable.changes_frozen ():
                variable.value = 1
            variable.value = 2

        self.assert_results (2)


    def test_changes_frozen_7 (self):
        variable     = Variable ()
        self.results = []

        variable.changed.connect (self.simple_handler)

        with variable.changes_frozen ():
            with variable.changes_frozen ():
                variable.value = 1
            variable.value = None

        # Must not emit: value returned to original.
        self.assert_results ()


    def test_derived_variable_changes_frozen_1 (self):
        DerivedVariable = AbstractVariable.derive_type ('DerivedVariable',
                                                        getter = lambda variable: x)
        x            = 1
        variable     = DerivedVariable ()
        self.results = []

        variable.store (self.simple_handler)

        with variable.changes_frozen ():
            x = 2

        # Though we never call _value_changed(), changes_frozen() promises to call it
        # itself in such cases.
        self.assert_results (1, 2)



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
