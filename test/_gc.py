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
import weakref

from notify.gc     import *
from test.__common import *



class WeaklyReferenceable (object):

    __slots__ = ('__weakref__')



class AbstractGCProtectorTestCase (NotifyTestCase):

    def test_default_property (self):
        original_protector = AbstractGCProtector.default
        self.assert_(isinstance (original_protector, AbstractGCProtector))

        try:
            new_protector = FastGCProtector ()
            AbstractGCProtector.set_default (new_protector)

            self.assert_(AbstractGCProtector.default is new_protector)

        finally:
            AbstractGCProtector.set_default (original_protector)



class _GCProtectorTestCase (NotifyTestCase):

    def _do_test_protection (self, protector):
        object    = WeaklyReferenceable ()
        reference = weakref.ref (object)

        self.assertNotEqual (reference (), None)

        protector.protect (object)
        del object

        self.collect_garbage ()
        self.assertNotEqual (reference (), None)

        protector.unprotect (reference ())

        self.collect_garbage ()
        self.assertEqual (reference (), None)


    def _do_test_double_protection (self, protector):
        object    = WeaklyReferenceable ()
        reference = weakref.ref (object)

        protector.protect (object)
        protector.protect (object)
        del object

        self.collect_garbage ()
        self.assertNotEqual (reference (), None)

        protector.unprotect (reference ())

        self.collect_garbage ()
        self.assertNotEqual (reference (), None)

        protector.unprotect (reference ())

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
