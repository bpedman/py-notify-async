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



class VariableDerivationTestCase (NotifyTestCase):

    def test_derivation_1 (self):
        IntVariable = Variable.derive_type ("IntVariable", allowed_value_types = (int,))

        # Since None is not an allowed value, there must be no default constructor.
        self.assertRaises (TypeError, lambda: IntVariable ())

        count = IntVariable (10)
        self.assertEqual (count.value, 10)
        self.assertEqual (count.mutable, True)

        count.value = 30
        self.assertEqual (count.value, 30)

        self.assertRaises (ValueError, lambda: count.set ('invalid'))


    def test_derivation_2 (self):
        EnumVariable = Variable.derive_type ("EnumVariable",
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
            "AbstractIntVariable", allowed_value_types = (int,))

        self.assertEqual (AbstractIntVariable (-5).mutable, False)


    def test_multiple_derivation (self):
        # Derive two types and make sure they don't spoil each other's is_allowed_value()
        # method.

        IntVariable = Variable.derive_type ("IntVariable", allowed_value_types = (int,))
        StrVariable = Variable.derive_type ("StrVariable", allowed_value_types = (str,))

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
