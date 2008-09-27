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


import sys
import unittest

from notify.bind   import Binding, WeakBinding, RaisingWeakBinding, \
                          CannotWeakReferenceError, GarbageCollectedError
from test.__common import NotifyTestCase



class Dummy (object):

    def identity_function (self, *arguments):
        return self.static_identity (*arguments)


    def static_identity (*arguments):
        if len (arguments) == 1:
            return arguments[0]
        else:
            return arguments

    def keyword_dict_function (self, **keywords):
        return self.static_keyword_dict (**keywords)

    def static_keyword_dict (**keywords):
        return keywords


    static_identity     = staticmethod (static_identity)
    static_keyword_dict = staticmethod (static_keyword_dict)



DUMMY = Dummy ()



class BindingTestCase (NotifyTestCase):

    def test_creation (self):
        Binding            (DUMMY.identity_function)
        WeakBinding        (DUMMY.identity_function)
        RaisingWeakBinding (DUMMY.identity_function)


    def test_invocation (self):
        self.assertEqual (Binding            (DUMMY.identity_function) (33, 'test'), (33, 'test'))
        self.assertEqual (WeakBinding        (DUMMY.identity_function) (33, 'test'), (33, 'test'))
        self.assertEqual (RaisingWeakBinding (DUMMY.identity_function) (33, 'test'), (33, 'test'))

    def test_invocation_keywords (self):
        keywords = { 'a': 1, 'b': 2 }
        self.assertEqual (Binding            (DUMMY.keyword_dict_function) (**keywords), keywords)
        self.assertEqual (WeakBinding        (DUMMY.keyword_dict_function) (**keywords), keywords)
        self.assertEqual (RaisingWeakBinding (DUMMY.keyword_dict_function) (**keywords), keywords)


    def test_creation_with_arguments (self):
        self.assertEqual (Binding (DUMMY.identity_function, (33,)) ('test'),
                          (33, 'test'))
        self.assertEqual (WeakBinding (DUMMY.identity_function, (33,)) ('test'),
                          (33, 'test'))
        self.assertEqual (RaisingWeakBinding (DUMMY.identity_function, (33,)) ('test'),
                          (33, 'test'))

    def test_creation_with_keywords (self):
        keywords = { 'a': 1, 'b': 2 }
        self.assertEqual (Binding (DUMMY.keyword_dict_function, (), keywords) (),
                          keywords)
        self.assertEqual (WeakBinding (DUMMY.keyword_dict_function, (), None, keywords) (),
                          keywords)
        self.assertEqual (RaisingWeakBinding (DUMMY.keyword_dict_function, (), None, keywords) (),
                          keywords)


    def test_unreferencable_object_method_failure (self):
        class Test (object):
            __slots__ = ()
            def test (self):
                pass

        self.assertRaises (CannotWeakReferenceError, lambda: WeakBinding        (Test ().test))
        self.assertRaises (CannotWeakReferenceError, lambda: RaisingWeakBinding (Test ().test))


    def test_equality_1 (self):
        for binding_type in (Binding, WeakBinding, RaisingWeakBinding):
            self.assert_equal_thoroughly (binding_type (DUMMY.identity_function),
                                          binding_type (DUMMY.identity_function))
            self.assert_equal_thoroughly (binding_type (Dummy.static_identity),
                                          binding_type (Dummy.static_identity))

            # We need to make sure objects don't get garbage collected before comparison.
            dummy1 = Dummy ()
            dummy2 = Dummy ()
            self.assert_not_equal_thoroughly (binding_type (dummy1.identity_function),
                                              binding_type (dummy2.identity_function))

            self.assert_not_equal_thoroughly (binding_type (DUMMY.identity_function),
                                              binding_type (DUMMY.static_identity))


    def test_equality_2 (self):
        # This test won't work on Python 3000, since unbound methods are gone.
        if sys.version_info[0] < 3:
            def f (x):
                pass

            class A (object):
                test = f

            class B (object):
                test = f

            for binding_type in (Binding, WeakBinding, RaisingWeakBinding):
                self.assert_not_equal_thoroughly (binding_type (A.test), binding_type (B.test))


    def test_equality_3 (self):
        for binding_type in (Binding, WeakBinding, RaisingWeakBinding):
            self.assert_equal_thoroughly (binding_type (DUMMY.identity_function, ('a', 'b', 'c')),
                                          binding_type (DUMMY.identity_function, ('a', 'b', 'c')))
            self.assert_equal_thoroughly (binding_type (DUMMY.static_identity, ('a', 'b', 'c')),
                                          binding_type (DUMMY.static_identity, ('a', 'b', 'c')))

            self.assert_not_equal_thoroughly (binding_type (DUMMY.identity_function,
                                                            ('a', 'b', 'c')),
                                              binding_type (DUMMY.identity_function,
                                                            ('a', 'b', 'd')))
            self.assert_not_equal_thoroughly (binding_type (Dummy.static_identity,
                                                            ('a', 'b', 'c')),
                                              binding_type (Dummy.static_identity,
                                                            ('a', 'b', 'd')))


    def test_equality_4 (self):
        def plain_function ():
            pass

        a_lambda = lambda: None

        for binding_type in (Binding, WeakBinding, RaisingWeakBinding):
            self.assert_equal_thoroughly (DUMMY.identity_function,
                                          binding_type (DUMMY.identity_function))
            self.assert_equal_thoroughly (DUMMY.static_identity,
                                          binding_type (DUMMY.static_identity))
            self.assert_equal_thoroughly (Dummy.static_identity,
                                          binding_type (Dummy.static_identity))
            self.assert_equal_thoroughly (Dummy.static_identity,
                                          binding_type (Dummy.static_identity))
            self.assert_equal_thoroughly (plain_function,
                                          binding_type (plain_function))
            self.assert_equal_thoroughly (a_lambda,
                                          binding_type (a_lambda))

            # Same as above, but with non-empty argument list.
            self.assert_not_equal_thoroughly (DUMMY.identity_function,
                                              binding_type (DUMMY.identity_function, (0,)))
            self.assert_not_equal_thoroughly (DUMMY.static_identity,
                                              binding_type (DUMMY.static_identity, (0,)))
            self.assert_not_equal_thoroughly (Dummy.static_identity,
                                              binding_type (Dummy.static_identity, (0,)))
            self.assert_not_equal_thoroughly (Dummy.static_identity,
                                              binding_type (Dummy.static_identity, (0,)))
            self.assert_not_equal_thoroughly (plain_function,
                                              binding_type (plain_function, (0,)))
            self.assert_not_equal_thoroughly (a_lambda,
                                              binding_type (a_lambda, (0,)))


    def test_equality_5 (self):
        keywords1 = { 'a': 1, 'b': 2 }
        keywords2 = { 'a': 1, 'b': 3 }

        for binding_type in (Binding, WeakBinding, RaisingWeakBinding):
            self.assert_equal_thoroughly (binding_type (DUMMY.identity_function,
                                                        keywords = keywords1),
                                          binding_type (DUMMY.identity_function,
                                                        keywords = keywords1))
            self.assert_equal_thoroughly (binding_type (DUMMY.static_identity,
                                                        keywords = keywords1),
                                          binding_type (DUMMY.static_identity,
                                                        keywords = keywords1))

            self.assert_not_equal_thoroughly (binding_type (DUMMY.identity_function,
                                                            keywords = keywords1),
                                              binding_type (DUMMY.identity_function,
                                                            keywords = keywords2))
            self.assert_not_equal_thoroughly (binding_type (Dummy.static_identity,
                                                            keywords = keywords1),
                                              binding_type (Dummy.static_identity,
                                                            keywords = keywords2))


    def test_garbage_collection_1 (self):
        object = Dummy ()
        method = WeakBinding (object.identity_function)

        self.assertEqual (method (15), 15)

        del object
        self.collect_garbage ()

        self.assertEqual (method (15), None)


    def test_garbage_collection_2 (self):
        object = Dummy ()
        method = RaisingWeakBinding (object.identity_function)

        self.assertEqual (method (15), 15)

        del object
        self.collect_garbage ()

        self.assertRaises (GarbageCollectedError, method)



class BindingWrapTestCase (NotifyTestCase):

    def test_wrap_1 (self):
        callable = lambda: None

        self.assert_(Binding           .wrap (callable) is callable)
        self.assert_(WeakBinding       .wrap (callable) is callable)
        self.assert_(RaisingWeakBinding.wrap (callable) is callable)


    def test_wrap_2 (self):
        callable = open

        self.assert_(Binding           .wrap (callable) is callable)
        self.assert_(WeakBinding       .wrap (callable) is callable)
        self.assert_(RaisingWeakBinding.wrap (callable) is callable)


    def test_wrap_3 (self):
        callable = Dummy.identity_function

        self.assert_(Binding           .wrap (callable) is callable)
        self.assert_(WeakBinding       .wrap (callable) is callable)
        self.assert_(RaisingWeakBinding.wrap (callable) is callable)


    def test_wrap_4 (self):
        callable = Dummy.static_identity

        self.assert_(Binding           .wrap (callable) is callable)
        self.assert_(WeakBinding       .wrap (callable) is callable)
        self.assert_(RaisingWeakBinding.wrap (callable) is callable)


    def test_wrap_5 (self):
        callable = DUMMY.identity_function

        for _class in (Binding, WeakBinding, RaisingWeakBinding):
            if issubclass (_class, WeakBinding):
                self.assert_(_class.wrap (callable) is not callable)

            self.assertEqual (_class.wrap (callable),        callable)
            self.assertEqual (_class.wrap (callable),        _class.wrap (callable))
            self.assertEqual (bool (_class.wrap (callable)), bool (callable))
            self.assertEqual (bool (_class.wrap (callable)), bool (_class.wrap (callable)))


    def test_wrap_6 (self):
        callable = DUMMY.identity_function

        if sys.version_info[0] >= 3:
            self.assert_(Binding.wrap (callable).__self__ is callable.__self__)
            self.assert_(Binding.wrap (callable).__func__ is callable.__func__)
        else:
            self.assert_(Binding.wrap (callable).im_self  is callable.im_self)
            self.assert_(Binding.wrap (callable).im_func  is callable.im_func)
            self.assert_(Binding.wrap (callable).im_class is callable.im_class)


    def test_wrap_with_arguments_1 (self):
        callable = lambda a, b, c: None

        self.assert_(Binding           .wrap (callable, (1, 2)) is not callable)
        self.assert_(WeakBinding       .wrap (callable, (1, 2)) is not callable)
        self.assert_(RaisingWeakBinding.wrap (callable, (1, 2)) is not callable)


    def test_wrap_with_keywords_1 (self):
        callable = lambda **keywords: None
        keywords = { 'a': 1, 'b': 2 }

        self.assert_(Binding           .wrap (callable, keywords = keywords) is not callable)
        self.assert_(WeakBinding       .wrap (callable, keywords = keywords) is not callable)
        self.assert_(RaisingWeakBinding.wrap (callable, keywords = keywords) is not callable)



if __name__ == '__main__':
    unittest.main ()



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
