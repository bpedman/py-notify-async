# -*- coding: utf-8 -*-

#--------------------------------------------------------------------#
# This file is part of Py-notify.                                    #
#                                                                    #
# Copyright (C) 2006, 2007 Paul Pogonyshev.                          #
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


"""
L{Variables <AbstractVariable>} hold any Python object and emit attached L{signal
<AbstractSignal>} when their value changes.

G{classtree AbstractVariable}
"""

__docformat__ = 'epytext en'
__all__       = ('AbstractVariable', 'AbstractValueTrackingVariable', 'Variable')


import types
import weakref

from notify.base      import *
from notify.condition import *
from notify.signal    import *
from notify.utils     import *



#-- Base variable classes --------------------------------------------

class AbstractVariable (AbstractValueObject):

    __slots__ = ()


    value = property (lambda self: self.get (), lambda self, value: self.set (value))


    def predicate (self, predicate):
        return _PredicateOverVariable (predicate, self)


    def is_true (self):
        return self.predicate (bool)

    def is_not_empty (self):
        return self.predicate (lambda sequence: sequence is not None and len (sequence) > 0)



    def __lt__(self, other):
        return self.get () <  other

    def __le__(self, other):
        return self.get () <= other

    def __ne__(self, other):
        return self.get () != other

    def __eq__(self, other):
        return self.get () == other

    def __gt__(self, other):
        return self.get () >  other

    def __ge__(self, other):
        return self.get () >= other

    def __cmp__(self, other):
        return self.get ().__cmp__(other)


    def __call__(self, callback):
        return self.get () (callback)


    def __len__(self):
        return len (self.get ())

    def __getitem__(self, key):
        return self.get () [key]

    def __setitem__(self, key, value):
        self.get () [key] = value

    def __delitem__(self, key):
        del self.get () [key]

    def __iter__(self):
        return self.get ().__iter__()

    def __contains__(self, item):
        return item in self.get ()


    # TODO: Emulate numeric types.



class AbstractValueTrackingVariable (AbstractVariable):

    __slots__ = ('_AbstractValueTrackingVariable__value')


    def __init__(self, initial_value = None):
        if not self.is_allowed_value (initial_value):
            raise ValueError ("`%s' is not allowed as value of the variable" % initial_value)

        super (AbstractValueTrackingVariable, self).__init__()
        self.__value = initial_value


    def get (self):
        return self.__value

    def _set (self, value):
        if self.get () != value:
            if not self.is_allowed_value (value):
                raise ValueError ("`%s' is not allowed as value of the variable" % value)

            self.__value = value
            return self._changed (value)

        else:
            return False


    def is_allowed_value (self, value):
        return True


    def _generate_derived_type_dictionary (self_class, options):
        allowed_values      = options.get ('allowed_values')
        allowed_value_types = options.get ('allowed_value_types')

        if allowed_value_types is not None:
            for allowed_type in allowed_value_types:
                if not isinstance (allowed_type, (type, types.ClassType)):
                    raise TypeError ("`allowed_value_types' must be a tuple of types and classes")

        for attribute in (super (AbstractValueTrackingVariable, self_class)
                          ._generate_derived_type_dictionary (options)):
            if attribute[0] != 'get':
                yield attribute

        functions = {}
        object    = options.get ('object')

        if allowed_values is not None or allowed_value_types is not None:
            if allowed_values is not None:
                if allowed_value_types is not None:
                    exec ('def is_allowed_value (self, value):\n'
                          '    return value in allowed_values\n'
                          '           and isinstance (value, allowed_value_types)') \
                          in options, functions
                else:
                    exec ('def is_allowed_value (self, value):\n'
                          '    return value in allowed_values\n') in options, functions
            else:
                exec ('def is_allowed_value (self, value):\n'
                      '    return isinstance (value, allowed_value_types)') in options, functions

        if 'getter' in options:
            if object is not None:
                exec (('def __init__ (self, %s):\n'
                       '    self_class.__init__ (self, getter (%s))\n'
                       '    %s = %s')
                      % (object, object, AbstractValueObject._get_object (options), object)) \
                      in options, functions
            else:
                exec ('def __init__ (self):\n'
                      '    self_class.__init__ (self, getter (self))\n') in options, functions

            exec (('def resynchronize_with_backend (self):\n'
                   '    self._set (getter (%s))')
                  % AbstractValueObject._get_object (options)) in options, functions

        else:
            # Since our is_allowed_value() implementation never accesses `self', it is OK
            # to pass None as that.
            if 'is_allowed_value' not in functions or functions['is_allowed_value'] (None, None):
                initial_default = ' = None'
            else:
                initial_default = ''

            if object is not None:
                exec (('def __init__ (self, %s, initial_value%s):\n'
                       '    self_class.__init__ (self, initial_value)\n'
                       '    %s = %s')
                      % (object, initial_default,
                         AbstractValueObject._get_object (options), object)) \
                      in options, functions
            else:
                exec (('def __init__ (self, initial_value%s):\n'
                       '    self_class.__init__ (self, initial_value)\n')
                      % initial_default) in options, functions

        for function in functions.iteritems ():
            yield function

        del functions
        del object


    _generate_derived_type_dictionary = classmethod (_generate_derived_type_dictionary)



#-- Standard non-abstract variable -----------------------------------

class Variable (AbstractValueTrackingVariable):

    __slots__ = ()


    def set (self, value):
        self._set (value)



#-- Internal variable classes -----------------------------------------

class _PredicateOverVariable (AbstractStateTrackingCondition):

    __slots__ = ('_PredicateOverVariable__predicate', '_PredicateOverVariable__variable')


    def __init__(self, predicate, variable):
        if not callable (predicate):
            raise TypeError ('predicate must be callable')

        super (_PredicateOverVariable, self).__init__(predicate (variable.get ()))

        self.__predicate = predicate
        self.__variable  = weakref.ref (variable, self.__on_usage_change)

        variable.signal_changed ().connect (self.__update)

    def __get_variable (self):
        return self.__variable ()


    def __update (self, new_value):
        self._set (self.__predicate (new_value))


    def _create_signal (self):
        if self.__variable () is not None:
            mark_object_as_used (self)

        signal = CleanSignal ()
        return signal, weakref.ref (signal, self.__on_usage_change)


    def __on_usage_change (self, object):
        self._remove_signal (object)

        if self._has_signal () or self.__variable () is not None:
            mark_object_as_unused (self)


    def _additional_description (self, formatter):
        return (['predicate: %s' % formatter (self.__predicate),
                 'variable: %s'  % formatter (self.__get_variable ())]
                + (super (_PredicateOverVariable, self)
                   ._additional_description (formatter)))



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
