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

from notify.mediator import BooleanMediator, FunctionalMediator


def wrap_argument (argument):
    return (argument,)



class MediatorValuesTestCase (unittest.TestCase):

    def test_double_value_mediator (self):
        mediator = BooleanMediator ('true', 'false')

        self.assertEqual (mediator.forward_value ('true'),  True)
        self.assertEqual (mediator.forward_value ('false'), False)

        self.assertEqual (mediator.forward (wrap_argument) ('true'),  (True,))
        self.assertEqual (mediator.forward (wrap_argument) ('false'), (False,))

        self.assertEqual (mediator.back_value (True),  'true')
        self.assertEqual (mediator.back_value (False), 'false')

        self.assertEqual (mediator.back (wrap_argument) (True),  ('true',))
        self.assertEqual (mediator.back (wrap_argument) (False), ('false',))

        # Now test some different values.

        self.assertEqual (mediator.forward_value (555), True)
        self.assertEqual (mediator.forward_value ([]),  False)

        self.assertEqual (mediator.forward (wrap_argument) (555), (True,))
        self.assertEqual (mediator.forward (wrap_argument) ([]),  (False,))


    def test_double_value_mediator_with_fallback (self):
        mediator = BooleanMediator ('TRUE', 'FALSE', lambda value: isinstance (value, str))

        self.assertEqual (mediator.forward_value ('TRUE'),  True)
        self.assertEqual (mediator.forward_value ('FALSE'), False)

        self.assertEqual (mediator.forward (wrap_argument) ('TRUE'),  (True,))
        self.assertEqual (mediator.forward (wrap_argument) ('FALSE'), (False,))

        self.assertEqual (mediator.back_value (True),  'TRUE')
        self.assertEqual (mediator.back_value (False), 'FALSE')

        self.assertEqual (mediator.back (wrap_argument) (True),  ('TRUE',))
        self.assertEqual (mediator.back (wrap_argument) (False), ('FALSE',))

        # Test some different values.  That's the point---test if
        # fallback function is called properly.

        self.assertEqual (mediator.forward_value (''), True)
        self.assertEqual (mediator.forward_value (67), False)

        self.assertEqual (mediator.forward (wrap_argument) (''), (True,))
        self.assertEqual (mediator.forward (wrap_argument) (67),  (False,))


    def test_functional_mediator (self):
        mediator = FunctionalMediator (lambda value: value + 100, lambda value: value - 100)

        self.assertEqual (mediator.forward_value (15), 115)
        self.assertEqual (mediator.back_value    (15), -85)

        self.assertEqual (mediator.forward (wrap_argument) (15), (115,))
        self.assertEqual (mediator.back    (wrap_argument) (15), (-85,))


    def test_reverse_mediator (self):
        mediator         = FunctionalMediator (lambda value: value + 100,
                                               lambda value: value - 100)
        reverse_mediator = mediator.reverse ()

        self.assertEqual (mediator.forward_value (reverse_mediator.forward_value (77)), 77)
        self.assertEqual (mediator.back_value    (reverse_mediator.back_value    (77)), 77)

        self.assertEqual (mediator.forward_value (reverse_mediator.back_value    (33)), 233)
        self.assertEqual (mediator.back_value    (reverse_mediator.forward_value (33)), -167)

        self.assertEqual (mediator.forward (reverse_mediator.forward (wrap_argument)) (77), (77,))
        self.assertEqual (mediator.back    (reverse_mediator.back    (wrap_argument)) (77), (77,))

        self.assertEqual (mediator.forward (reverse_mediator.back    (wrap_argument)) (33), (233,))
        self.assertEqual (mediator.back    (reverse_mediator.forward (wrap_argument)) (33), (-167,))


    def test_double_reverse_mediator (self):
        mediator1 = FunctionalMediator (lambda value: value + 100, lambda value: value - 100)
        mediator2 = mediator1.reverse ().reverse ()

        self.assertEqual (mediator1.forward_value (10), mediator2.forward_value (10))
        self.assertEqual (mediator1.back_value    (10), mediator2.back_value    (10))

        self.assertEqual (mediator1.forward (wrap_argument) (10),
                          mediator2.forward (wrap_argument) (10))
        self.assertEqual (mediator1.back    (wrap_argument) (10),
                          mediator2.back    (wrap_argument) (10))



class MediatorFunctionsTestCase (unittest.TestCase):

    def test_double_value_mediator_basic_equality (self):
        self.do_test_basic_equality (BooleanMediator ('true', 'false'))

    def test_functional_mediator_basic_equality (self):
        self.do_test_basic_equality (FunctionalMediator (lambda value: value + 100,
                                                         lambda value: value - 100))


    def do_test_basic_equality (self, mediator):
        self.assertEqual (mediator.forward (wrap_argument), mediator.forward (wrap_argument))
        self.assertEqual (mediator.back    (wrap_argument), mediator.back    (wrap_argument))



if __name__ == '__main__':
    unittest.main ()



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
