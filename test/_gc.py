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
import weakref

from notify.gc     import AbstractGCProtector, FastGCProtector, DebugGCProtector, RaisingGCProtector
from test.__common import NotifyTestCase



class WeaklyReferenceable (object):

    __slots__ = ('__weakref__')



class AbstractGCProtectorTestCase (NotifyTestCase):

    def test_default_property (self):
        original_protector = AbstractGCProtector.default
        self.assert_(isinstance (original_protector, AbstractGCProtector))

        try:
            new_protector = FastGCProtector ()
            AbstractGCProtector.default = new_protector

            self.assert_(AbstractGCProtector.default is new_protector)

        finally:
            AbstractGCProtector.default = original_protector


    def test_default_property_illegals (self):
        def create_assigner (value):
            def assigner ():
                AbstractGCProtector.default = value
            return assigner

        self.assertRaises (ValueError, create_assigner (42))

        # When current default protector is in use, it cannot be replaced.
        AbstractGCProtector.default.protect (42)
        self.assertRaises (ValueError, create_assigner (FastGCProtector ()))
        AbstractGCProtector.default.unprotect (42)



class _GCProtectorTestCase (NotifyTestCase):

    def _do_test_protection (self, protector):
        object    = WeaklyReferenceable ()
        reference = weakref.ref (object)

        self.assertEqual (protector.num_active_protections, 0)
        if isinstance (protector, RaisingGCProtector):
            self.assertEqual (protector.get_num_object_protections (object), 0)
            self.assertEqual (protector.num_protected_objects, 0)

        self.assertNotEqual (reference (), None)

        protector.protect (object)

        self.assertEqual (protector.num_active_protections, 1)
        if isinstance (protector, RaisingGCProtector):
            self.assertEqual (protector.get_num_object_protections (object), 1)
            self.assertEqual (protector.num_protected_objects, 1)

        del object

        self.collect_garbage ()
        self.assertNotEqual (reference (), None)

        protector.unprotect (reference ())

        self.assertEqual (protector.num_active_protections, 0)
        if isinstance (protector, RaisingGCProtector):
            self.assertEqual (protector.num_protected_objects, 0)

        self.collect_garbage ()
        self.assertEqual (reference (), None)


    def _do_test_double_protection (self, protector):
        object    = WeaklyReferenceable ()
        reference = weakref.ref (object)

        self.assertEqual (protector.num_active_protections, 0)
        if isinstance (protector, RaisingGCProtector):
            self.assertEqual (protector.get_num_object_protections (object), 0)
            self.assertEqual (protector.num_protected_objects, 0)

        protector.protect (object)

        self.assertEqual (protector.num_active_protections, 1)
        if isinstance (protector, RaisingGCProtector):
            self.assertEqual (protector.get_num_object_protections (object), 1)
            self.assertEqual (protector.num_protected_objects, 1)

        protector.protect (object)

        self.assertEqual (protector.num_active_protections, 2)
        if isinstance (protector, RaisingGCProtector):
            self.assertEqual (protector.get_num_object_protections (object), 2)
            self.assertEqual (protector.num_protected_objects, 1)

        del object

        self.collect_garbage ()
        self.assertNotEqual (reference (), None)

        protector.unprotect (reference ())

        self.assertEqual (protector.num_active_protections, 1)
        if isinstance (protector, RaisingGCProtector):
            self.assertEqual (protector.num_protected_objects, 1)

        self.collect_garbage ()
        self.assertNotEqual (reference (), None)

        protector.unprotect (reference ())

        self.assertEqual (protector.num_active_protections, 0)
        if isinstance (protector, RaisingGCProtector):
            self.assertEqual (protector.num_protected_objects, 0)

        self.collect_garbage ()
        self.assertEqual (reference (), None)



class FastGCProtectorTestCase (_GCProtectorTestCase):

    def test_protection_1 (self):
        self._do_test_protection (FastGCProtector ())

    def test_protection_2 (self):
        self._do_test_double_protection (FastGCProtector ())



class RaisingGCProtectorTestCase (_GCProtectorTestCase):

    def test_protection_1 (self):
        self._do_test_protection (RaisingGCProtector ())

    def test_protection_2 (self):
        self._do_test_double_protection (RaisingGCProtector ())

    def test_protection_3 (self):
        protector = RaisingGCProtector ()
        a         = 1
        b         = 2

        self.assertRaises (ValueError, lambda: protector.unprotect (a))

        protector.protect (a)
        self.assertRaises (ValueError, lambda: protector.unprotect (b))

        protector.unprotect (a)
        self.assertRaises (ValueError, lambda: protector.unprotect (a))



class DebugGCProtectorTestCase (_GCProtectorTestCase):

    def test_protection_1 (self):
        self._do_test_protection (DebugGCProtector ())

    def test_protection_2 (self):
        self._do_test_double_protection (DebugGCProtector ())



if __name__ == '__main__':
    unittest.main ()



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
