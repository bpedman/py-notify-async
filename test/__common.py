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


import gc
import unittest
import weakref

from notify.gc    import AbstractGCProtector
from notify.utils import _PYTHON_IMPLEMENTATION


__all__ = ('NotifyTestObject', 'NotifyTestCase', 'ignoring_exceptions')



# Each test should create an instance of this class and connect handlers defined here.
# The reason is that conditions, variables etc. are garbage-collected only after last
# handler dies.  If handlers belong to an object which is in test function scope,
# everything used by the test will be GC-collected after test finishes.  Else we can have
# dangling conditions, which will prevent us from changing `AbstractGCProtector.default',
# among other things.
class NotifyTestObject (object):

    def __init__(self):
        self.results = []


    def assert_results (self, *results):
        valid_results = list (results)

        if self.results != valid_results:
            raise AssertionError ('results: %s; expected: %s' % (self.results, valid_results))


    def simple_handler (self, *arguments):
        if len (arguments) == 1:
            arguments = arguments[0]

        self.results.append (arguments)

    def simple_handler_100 (self, *arguments):
        self.simple_handler (100 + arguments[0])


    def simple_handler_200 (self, *arguments):
        self.simple_handler (200 + arguments[0])


    def simple_keywords_handler (self, *arguments, **keywords):
        if arguments:
            arguments = arguments + (keywords,)
            self.results.append (arguments)
        else:
            self.results.append (keywords)



class NotifyTestCase (unittest.TestCase):

    HAVE_CONTROLLABLE_GC = (_PYTHON_IMPLEMENTATION == 'CPython')

    try:
        weakref.ref (object ())
        ALL_OBJECTS_ARE_WEAKLY_REFERABLE = True
    except TypeError:
        ALL_OBJECTS_ARE_WEAKLY_REFERABLE = False

    REASON_OLD_PYTHON                 = 'because they require a later Python version to run'
    REASON_INVALID_FOR_IMPLEMENTATION = 'because they are not valid for your Python implementation'

    __test_skip_reasons = []


    def setUp (self):
        super (NotifyTestCase, self).setUp ()

        if not self.HAVE_CONTROLLABLE_GC:
            return

        gc.set_threshold (0, 0, 0)

        self.__num_collectable_objects = self.collect_garbage ()
        self.__num_active_protections  = AbstractGCProtector.default.num_active_protections


    # It is important to leave no garbage behind, since `AbstractGCProtector.default' is
    # only assignable in 'fresh' state.  Tests also must be self-contained, therefore we
    # check that tests don't leave new garbage-collectable objects or GC protections.
    # Those almost certainly indicate a memory leak.
    def tearDown (self):
        super (NotifyTestCase, self).tearDown ()

        if not self.HAVE_CONTROLLABLE_GC:
            return

        num_collectable_objects = self.collect_garbage ()
        if num_collectable_objects != self.__num_collectable_objects:
            raise ValueError (('number of garbage-collectable objects before and after the test '
                               'differ: %d != %d')
                              % (self.__num_collectable_objects, num_collectable_objects))

        if AbstractGCProtector.default.num_active_protections != self.__num_active_protections:
            raise ValueError (('number of active GC protections before and after the test differ: '
                               '%d != %d')
                              % (self.__num_active_protections,
                                 AbstractGCProtector.default.num_active_protections))


    def non_existing_attribute_setter (self, object, name = 'this_attribute_sure_doesnt_exist'):
        return lambda: setattr (object, name, None)


    def assert_equal_thoroughly (self, value1, value2):
        self.assert_(    value1 == value2)
        self.assert_(not value1 != value2)

        try:
            hash1 = hash (value1)
            hash2 = hash (value2)

        except TypeError:
            # It is OK, at least one value is unhashable then.
            pass

        else:
            self.assert_(hash1 == hash2)


    def assert_not_equal_thoroughly (self, value1, value2):
        self.assert_(    value1 != value2)
        self.assert_(not value1 == value2)

        # Note: hashes are _not_ required to be different, so don't test them.


    def collect_garbage (self):
        if not self.HAVE_CONTROLLABLE_GC:
            # Just try hard and hope it works.  FIXME: Inadequate.
            for iteration in range (10):
                gc.collect ()
            return 0

        def count_garbage_collectable_objects ():
            return len ([object for object in gc.get_objects ()
                         if type (object).__module__.startswith ('notify.')])

        num_objects = count_garbage_collectable_objects ()

        # TODO: Account for 'statics' like notify.Condition.TRUE.  Condition below is
        #       always false due to these 'statics'.
        if num_objects == 0:
            return 0

        num_passes  = 0
        while num_passes < 20:
            gc.collect ()
            num_objects_new = count_garbage_collectable_objects ()

            if num_objects_new < num_objects:
                num_objects  = num_objects_new
                num_passes  += 1
            else:
                return num_objects

        # If we spent a lot of passes, something is probably wrong.
        return -1


    def note_skipped_tests (tests_defined = False, reason = REASON_OLD_PYTHON):
        if tests_defined:
            return True

        if not NotifyTestCase.__test_skip_reasons:
            import sys
            import atexit

            def announce_test_skipping ():
                sys.stdout.write ('\n')
                for reason in NotifyTestCase.__test_skip_reasons:
                    sys.stdout.write ('Some tests were skipped %s\n' % reason)

            atexit.register (announce_test_skipping)

        if reason not in NotifyTestCase.__test_skip_reasons:
            NotifyTestCase.__test_skip_reasons.append (reason)

        return False


    note_skipped_tests = staticmethod (note_skipped_tests)



import __future__


if 'with_statement' in __future__.all_feature_names:

    class ignoring_exceptions (object):
        def __enter__(self):
            pass
        def __exit__(self, *exception_info):
            return True

else:
    def ignoring_exceptions (object):
        raise RuntimeError ('ignoring_exceptions() must not be used in pre-Python 2.5 tests')



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
