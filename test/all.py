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

import types

from notify.all    import *
from test.__common import NotifyTestCase



class AllTestCase (NotifyTestCase):

    def assert_is_function (self, function):
        self.assert_(isinstance (function, (types.FunctionType, types.BuiltinFunctionType)))


    def assert_is_class (self, _class):
        if issubclass (_class, Exception):
            self.assert_(isinstance (_class, ClassTypes), _class)

        else:
            self.assert_(isinstance (_class, type), _class)

            # Also assert that classes define `__slots__' variable appropriately.  We use
            # a trick hoping that constructor of `_class' accepts a number of `None'
            # values.  Thus, not all classes are tested.

            for num_arguments in range (0, 10):
                try:
                    object = _class (* ((None,) * num_arguments))
                except:
                    continue

                self.assertRaises (AttributeError, self.non_existing_attribute_setter (object))
                break


    def test_base (self):
        self.assert_is_class (AbstractValueObject)


    def test_bind (self):
        self.assert_is_class (Binding)
        self.assert_is_class (WeakBinding)
        self.assert_is_class (RaisingWeakBinding)

        for type in BindingCompatibleTypes:
            self.assert_is_class (type)

        self.assert_is_class (CannotWeakReferenceError)
        self.assert_is_class (GarbageCollectedError)


    def test_condition (self):
        self.assert_is_class (AbstractCondition)
        self.assert_is_class (AbstractStateTrackingCondition)
        self.assert_is_class (Condition)
        self.assert_is_class (PredicateCondition)
        self.assert_is_class (WatcherCondition)


    def test_gc (self):
        self.assert_is_class (AbstractGCProtector)
        self.assert_is_class (FastGCProtector)
        self.assert_is_class (DebugGCProtector)


    def test_mediator (self):
        self.assert_is_class (AbstractMediator)
        self.assert_is_class (BooleanMediator)
        self.assert_is_class (FunctionalMediator)


    def test_signal (self):
        self.assert_is_class (AbstractSignal)
        self.assert_is_class (Signal)
        self.assert_is_class (CleanSignal)


    def test_util (self):
        self.assert_is_function (is_callable)
        self.assert_is_function (is_valid_identifier)
        self.assert_is_function (mangle_identifier)

         # It is not a function, not a class...  Just test it is there.
        self.assert_            (as_string)

        self.assert_is_function (raise_not_implemented_exception)
        self.assert_is_class    (DummyReference)

    def test_variable (self):
        self.assert_is_class (AbstractVariable)
        self.assert_is_class (AbstractValueTrackingVariable)
        self.assert_is_class (Variable)
        self.assert_is_class (WatcherVariable)



if __name__ == '__main__':
    unittest.main ()



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
