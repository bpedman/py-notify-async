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
__all__       = ('AbstractVariable', 'AbstractValueTrackingVariable',
                 'Variable', 'WatcherVariable')


import types
import weakref

from notify.base      import *
from notify.condition import *
from notify.gc        import *
from notify.signal    import *



#-- Base variable classes --------------------------------------------

class AbstractVariable (AbstractValueObject):

    """
    Abstract base class of variable hierarchy tree.  All variable derive from this class,
    so you should use C{isinstance (..., AbstractVariable)}, not
    C{isinstance (..., Variable)}.
    """

    __slots__ = ()


    value = property (lambda self: self.get (), lambda self, value: self.set (value),
                      doc = ("""
                             The current value of the variable.  This property is
                             writable, but setting it for immutable variables will raise
                             C{NotImplementedError}.

                             @type: object
                             """))


    def predicate (self, predicate):
        return _PredicateOverVariable (predicate, self)


    def is_true (self):
        return self.predicate (bool)

    def is_not_empty (self):
        return self.predicate (lambda sequence: sequence is not None and len (sequence) > 0)



class AbstractValueTrackingVariable (AbstractVariable):

    """
    A variable that stores its value instead of recomputing it each time.  Since there is
    no public way to alter variable’s value, this class is still abstract.  For a generic
    mutable variable implementation, see C{L{Variable}} class.
    """

    __slots__ = ('_AbstractValueTrackingVariable__value')


    def __init__(self, initial_value = None):
        """
        Initialize a new variable with specified C{initial_value}.  The value must conform
        to restrictions (if any) specified in C{L{is_allowed_value}} method.

        @raises ValueError: if C{initial_value} is not suitable per C{L{is_allowed_value}}
                            method.
        """

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
            return self._value_changed (value)

        else:
            return False


    def is_allowed_value (self, value):
        """
        Determine if C{value} is suitable for this variable.  Default implementation
        always returns C{True}, regardless of its only argument.  So, to restrict
        variable’s value set, you need to create a new variable type, either using
        C{L{derive_type}} method or directly.

        @rtype: bool
        """

        return True


    def _generate_derived_type_dictionary (self_class, options):
        allowed_values      = options.get ('allowed_values')
        allowed_value_types = options.get ('allowed_value_types')

        if allowed_value_types is not None:
            if not isinstance (allowed_value_types, tuple):
                allowed_value_types = (allowed_value_types,)

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
                exec (('def __init__(self, %s):\n'
                       '    self_class.__init__(self, getter (%s))\n'
                       '    %s = %s')
                      % (object, object, AbstractValueObject._get_object (options), object)) \
                      in options, functions
            else:
                exec ('def __init__(self):\n'
                      '    self_class.__init__(self, getter (self))\n') in options, functions

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
                exec (('def __init__(self, %s, initial_value%s):\n'
                       '    self_class.__init__(self, initial_value)\n'
                       '    %s = %s')
                      % (object, initial_default,
                         AbstractValueObject._get_object (options), object)) \
                      in options, functions
            else:
                exec (('def __init__(self, initial_value%s):\n'
                       '    self_class.__init__(self, initial_value)\n')
                      % initial_default) in options, functions

        for function in functions.iteritems ():
            yield function

        del functions
        del object


    _generate_derived_type_dictionary = classmethod (_generate_derived_type_dictionary)



#-- Standard non-abstract variables ----------------------------------

class Variable (AbstractValueTrackingVariable):

    __slots__ = ()


    def set (self, value):
        self._set (value)



class WatcherVariable (AbstractValueTrackingVariable):

    __slots__ = ('_WatcherVariable__watched_variable')


    def __init__(self, variable_to_watch = None):
        super (WatcherVariable, self).__init__(None)

        self.__watched_variable = None
        self.watch (variable_to_watch)


    def watch (self, variable_to_watch):
        if (variable_to_watch is not None
            and (   not isinstance (variable_to_watch, AbstractVariable)
                 or variable_to_watch is self)):
            raise TypeError ('can only watch other variables')

        watched_variable = self.__get_watched_variable ()
        if watched_variable is not None:
            watched_variable.changed.disconnect (self._set)

        if variable_to_watch is not None:
            self.__watched_variable = weakref.ref (variable_to_watch, self.__on_usage_change)
            variable_to_watch.store (self._set)
        else:
            self.__watched_variable = None
            self._set (None)

        if self._has_signal ():
            if watched_variable is None and variable_to_watch is not None:
                AbstractGCProtector.default.protect (self)
            elif watched_variable is not None and variable_to_watch is None:
                AbstractGCProtector.default.unprotect (self)


    def __get_watched_variable (self):
        if self.__watched_variable is not None:
            return self.__watched_variable ()
        else:
            return None


    def _create_signal (self):
        if self.__get_watched_variable () is not None:
            AbstractGCProtector.default.protect (self)

        signal = CleanSignal (self)
        return signal, weakref.ref (signal, self.__on_usage_change)


    def __on_usage_change (self, object):
        # Complexities because watched variable can change and this function may be called
        # on previously watched variable.

        if self._remove_signal (object):
            if self.__get_watched_variable () is not None:
                AbstractGCProtector.default.unprotect (self)
        else:
            if object is self.__watched_variable:
                self.__watched_variable = None

                if self._has_signal ():
                    AbstractGCProtector.default.unprotect (self)


    def _additional_description (self, formatter):
        return (['watching %s' % formatter (self.__get_watched_variable ())]
                + super (WatcherVariable, self)._additional_description (formatter))



#-- Internal variable classes -----------------------------------------

class _PredicateOverVariable (AbstractStateTrackingCondition):

    __slots__ = ('_PredicateOverVariable__predicate', '_PredicateOverVariable__variable')


    def __init__(self, predicate, variable):
        if not callable (predicate):
            raise TypeError ('predicate must be callable')

        super (_PredicateOverVariable, self).__init__(predicate (variable.get ()))

        self.__predicate = predicate
        self.__variable  = weakref.ref (variable, self.__on_usage_change)

        variable.changed.connect (self.__update)

    def __get_variable (self):
        return self.__variable ()


    def __update (self, new_value):
        self._set (self.__predicate (new_value))


    def _create_signal (self):
        if self.__variable () is not None:
            AbstractGCProtector.default.protect (self)

        signal = CleanSignal (self)
        return signal, weakref.ref (signal, self.__on_usage_change)


    def __on_usage_change (self, object):
        self._remove_signal (object)

        if self._has_signal () or self.__variable () is not None:
            AbstractGCProtector.default.unprotect (self)


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
