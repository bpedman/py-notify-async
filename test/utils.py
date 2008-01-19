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

from notify.utils import is_callable, is_valid_identifier, mangle_identifier, as_string, \
                         raise_not_implemented_exception, DummyReference



class UtilsTestCase (unittest.TestCase):

    def test_is_callable (self):
        self.assert_(is_callable (is_callable))
        self.assert_(is_callable (UtilsTestCase))
        self.assert_(is_callable (UtilsTestCase.test_is_callable))

        self.assert_(not is_callable (None))
        self.assert_(not is_callable (5))
        self.assert_(not is_callable ('foo'))
        self.assert_(not is_callable ([]))


    def test_is_valid_identifier (self):
        self.assert_(is_valid_identifier ('foo'))
        self.assert_(is_valid_identifier ('_foo'))
        self.assert_(is_valid_identifier ('__foo'))
        self.assert_(is_valid_identifier ('foo2'))
        self.assert_(is_valid_identifier ('foo_bar'))
        self.assert_(is_valid_identifier ('FooBar'))
        self.assert_(is_valid_identifier ('fooBar'))

        self.assert_(not is_valid_identifier (''))
        self.assert_(not is_valid_identifier ('2foo'))
        self.assert_(not is_valid_identifier ('foo bar'))
        self.assert_(not is_valid_identifier ('foo.bar'))
        self.assert_(not is_valid_identifier ('-fooBar'))
        self.assert_(not is_valid_identifier ('foo_bar '))

        # Keywords are not valid identifiers.
        self.assert_(not is_valid_identifier ('class'))
        self.assert_(not is_valid_identifier ('def'))
        self.assert_(not is_valid_identifier ('in'))
        self.assert_(not is_valid_identifier ('and'))

        self.assert_(not is_valid_identifier (None))
        self.assert_(not is_valid_identifier (1))
        self.assert_(not is_valid_identifier (()))
        self.assert_(not is_valid_identifier ([]))


    def test_mangle_identifier (self):
        self.assertEqual (mangle_identifier ('Foo',     'bar'),     'bar')
        self.assertEqual (mangle_identifier ('_Foo',    'bar'),     'bar')
        self.assertEqual (mangle_identifier ('__Foo',   'bar'),     'bar')
        self.assertEqual (mangle_identifier ('__Foo__', 'bar'),     'bar')
        self.assertEqual (mangle_identifier ('Foo',     '_bar'),    '_bar')
        self.assertEqual (mangle_identifier ('_Foo',    '_bar'),    '_bar')
        self.assertEqual (mangle_identifier ('__Foo',   '_bar'),    '_bar')
        self.assertEqual (mangle_identifier ('__Foo__', '_bar'),    '_bar')
        self.assertEqual (mangle_identifier ('Foo',     '__bar'),   '_Foo__bar')
        self.assertEqual (mangle_identifier ('_Foo',    '__bar'),   '_Foo__bar')
        self.assertEqual (mangle_identifier ('__Foo',   '__bar'),   '_Foo__bar')
        self.assertEqual (mangle_identifier ('__Foo__', '__bar'),   '_Foo____bar')
        self.assertEqual (mangle_identifier ('Foo',     '__bar__'), '__bar__')
        self.assertEqual (mangle_identifier ('_Foo',    '__bar__'), '__bar__')
        self.assertEqual (mangle_identifier ('__Foo',   '__bar__'), '__bar__')
        self.assertEqual (mangle_identifier ('__Foo__', '__bar__'), '__bar__')

        # Special cases.
        self.assertEqual (mangle_identifier ('_',     '__bar'),   '__bar')
        self.assertEqual (mangle_identifier ('__',    '__bar'),   '__bar')
        self.assertEqual (mangle_identifier ('___',   '__bar'),   '__bar')
        self.assertEqual (mangle_identifier ('Foo',   '__'),      '__')
        self.assertEqual (mangle_identifier ('___',   '_____'),   '_____')


    def test_as_string (self):
        self.assertEqual (as_string.foo,     'foo')
        self.assertEqual (as_string._foo,    '_foo')
        self.assertEqual (as_string.__foo,   '_UtilsTestCase__foo')
        self.assertEqual (as_string.__foo__, '__foo__')


    def test_as_string_attributes (self):
        def set_as_string_attribute ():
            as_string.foo = 'bar'

        def del_as_string_attribute ():
            del as_string.foo

        self.assertRaises (TypeError, set_as_string_attribute)
        self.assertRaises (TypeError, del_as_string_attribute)

        self.assertEqual  (dir (as_string), [])


    def test_raise_non_implemented_exception (self):
        self.assertRaises (NotImplementedError,
                           lambda: raise_not_implemented_exception ())
        self.assertRaises (NotImplementedError,
                           lambda: raise_not_implemented_exception (self))
        self.assertRaises (NotImplementedError,
                           lambda: raise_not_implemented_exception (self, 'foo'))
        self.assertRaises (NotImplementedError,
                           lambda: raise_not_implemented_exception (self, 1))


    def test_dummy_reference (self):
        self.assert_(is_callable (DummyReference (None)))
        self.assert_(DummyReference (None) () is None)

        self.assert_(is_callable (DummyReference (self)))
        self.assert_(DummyReference (self) () is self)



if __name__ == '__main__':
    unittest.main ()



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
