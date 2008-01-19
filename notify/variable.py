# -*- coding: utf-8 -*-

#--------------------------------------------------------------------#
# This file is part of Py-notify.                                    #
#                                                                    #
# Copyright (C) 2006, 2007, 2008 Paul Pogonyshev.                    #
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

from notify.base      import AbstractValueObject
from notify.condition import AbstractStateTrackingCondition
from notify.gc        import AbstractGCProtector
from notify.signal    import CleanSignal
from notify.utils     import execute, is_callable, ClassTypes



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
        """
        Construct a condition, whose state is always given C{predicate} over this variable
        value.

        @param  predicate: a callable accepting one argument (current value) which
                           determines the state of the returned condition.

        @rtype:            C{L{AbstractCondition}}

        @raises TypeError: if C{predicate} is not callable.
        """

        return _PredicateOverVariable (predicate, self)


    def transform (self, transformer):
        """
        Construct a variable, whose state is always given transformation of this variable
        value.

        @param  transformer: a callable accepting one argument (current value) which
                             computes derived value of the returned variable.

        @rtype:              C{L{AbstractVariable}}

        @raises TypeError:   if C{transformer} is not callable.
        """

        return _VariableTransformation (transformer, self)


    def is_true (self):
        """
        Identical to C{L{predicate} (bool)}.  It was decided to have a separate function
        rather than provide default value for the only argument of C{predicate} only for a
        better name.

        @rtype: C{L{AbstractCondition}}
        """

        return self.predicate (bool)



class AbstractValueTrackingVariable (AbstractVariable):

    """
    A variable that stores its value instead of recomputing it each time.  Since there is
    no public way to alter variable’s value, this class is still abstract.  For a generic
    mutable variable implementation, see C{L{Variable}} class.
    """

    __slots__ = ('__value')


    def __init__(self, initial_value = None):
        """
        Initialize a new variable with specified C{initial_value}.  The value must conform
        to restrictions (if any) specified in C{L{is_allowed_value}} method.

        @param  initial_value: initial value for this variable.
        @type   initial_value: C{object}

        @raises ValueError:    if C{initial_value} is not suitable according to
                               C{L{is_allowed_value}} method.
        """

        if not self.is_allowed_value (initial_value):
            raise ValueError ("'%s' is not allowed as value of the variable" % initial_value)

        super (AbstractValueTrackingVariable, self).__init__()
        self.__value = initial_value


    def get (self):
        """
        Get the current value of the variable.  Since this variable type stores its value,
        this is the last object as passed to C{L{_set}} method internally.

        @rtype: C{object}
        """

        return self.__value

    def _set (self, value):
        """
        Set the value of the variable internally.  The C{value} is checked for both
        equality with the current value and whether it passes C{L{is_allowed_value}} test.
        So, this method does all that is needed for C{set} method of a mutable variable.

        This method I{must not} be used from outside.  For mutable variables, use C{set}
        instead; immutable ones update their values through other means.

        @param  value:      new value for the variable.
        @type   value:      C{object}

        @rtype:             C{bool}
        @returns:           Whether variable value changed as a result.

        @raises ValueError: if C{value} is not acceptable according to
                            C{L{is_allowed_value}}.
        """

        if self.get () != value:
            if not self.is_allowed_value (value):
                raise ValueError ("'%s' is not allowed as value of the variable" % value)

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

        @param value: candidate for the value of self variable.
        @type  value: C{object}

        @rtype:       C{bool}
        """

        return True


    def _generate_derived_type_dictionary (cls, options):
        allowed_values      = options.get ('allowed_values')
        allowed_value_types = options.get ('allowed_value_types')

        if allowed_value_types is not None:
            if not isinstance (allowed_value_types, tuple):
                allowed_value_types = (allowed_value_types,)

            for allowed_type in allowed_value_types:
                if not isinstance (allowed_type, ClassTypes):
                    raise TypeError ("'allowed_value_types' must be a tuple of types and classes")

        for attribute in (super (AbstractValueTrackingVariable, cls)
                          ._generate_derived_type_dictionary (options)):
            if attribute[0] not in ('get', 'set'):
                yield attribute

        functions        = {}
        object           = options.get ('object')
        filtered_options = AbstractValueObject._filter_options (options,
                                                                'cls',
                                                                'allowed_values',
                                                                'allowed_value_types',
                                                                'getter', 'setter',
                                                                'default_value')

        if allowed_values is not None or allowed_value_types is not None:
            if allowed_values is not None:
                if allowed_value_types is not None:
                    execute ('def is_allowed_value (self, value):\n'
                             '    return value in allowed_values\n'
                             '           and isinstance (value, allowed_value_types)',
                             filtered_options, functions)
                else:
                    execute ('def is_allowed_value (self, value):\n'
                             '    return value in allowed_values\n',
                             filtered_options, functions)
            else:
                execute ('def is_allowed_value (self, value):\n'
                         '    return isinstance (value, allowed_value_types)',
                         filtered_options, functions)

        if 'getter' in options:
            if object is not None:
                execute (('def __init__(self, %s):\n'
                          '    cls.__init__(self, getter (%s))\n'
                          '    %s = %s')
                         % (object, object, AbstractValueObject._get_object (options), object),
                         filtered_options, functions)
            else:
                execute ('def __init__(self):\n'
                         '    cls.__init__(self, getter (self))\n',
                         filtered_options, functions)

            execute (('def resynchronize_with_backend (self):\n'
                      '    self._set (getter (%s))')
                     % AbstractValueObject._get_object (options),
                     filtered_options, functions)

        else:
            if 'default_value' in options:
                if (    'is_allowed_value' in functions
                    and not functions['is_allowed_value'] (None, options['default_value'])):
                   raise ValueError ("'default_value' of '%s' is not within allowed value set"
                                     % (options['default_value'],))

                initial_default = ' = default_value'

            # Since our is_allowed_value() implementation never accesses `self', it is OK
            # to pass None as that.
            elif 'is_allowed_value' not in functions or functions['is_allowed_value'] (None, None):
                initial_default = ' = None'

            else:
                initial_default = ''

            if 'setter' in options:
                setter_statement = ('setter (%s, initial_value)'
                                    % AbstractValueObject._get_object (options))
            else:
                setter_statement = ''

            if object is not None:
                execute (('def __init__(self, %s, initial_value%s):\n'
                          '    cls.__init__(self, initial_value)\n'
                          '    %s = %s\n'
                          '    %s\n')
                         % (object, initial_default,
                            AbstractValueObject._get_object (options), object, setter_statement),
                         filtered_options, functions)
            else:
                execute (('def __init__(self, initial_value%s):\n'
                          '    cls.__init__(self, initial_value)\n'
                          '    %s\n')
                         % (initial_default, setter_statement),
                         filtered_options, functions)

        if 'setter' in options:
            execute (('def _set (self, value):\n'
                      '    if self.get () != value:\n'
                      '        if not self.is_allowed_value (value):\n'
                      '            raise ValueError \\\n'
                      '                ("\'%%s\' is not allowed as value of the variable" %% value)\n'
                      '        setter (%s, value)\n'
                      '        self._AbstractValueTrackingVariable__value = value\n'
                      '        return self._value_changed (value)\n'
                      '    else:\n'
                      '        return False')
                     % AbstractValueObject._get_object (options),
                     filtered_options, functions)

            execute ('def set (self, value): return self._set (value)', functions)

        for function in functions.items ():
            yield function


    _generate_derived_type_dictionary = classmethod (_generate_derived_type_dictionary)



#-- Standard non-abstract variables ----------------------------------

class Variable (AbstractValueTrackingVariable):

    """
    Standard implementation of a mutable variable.  It is an all-purpose class suitable
    for almost any use.  In particular, you may not derive new variable types and just use
    mutable variables everywhere.  Deriving new types is more ‘proper’ and can make
    difference if you have some code that differentiates between mutable and immutable
    variables, but using this class is somewhat simpler.  Additionally, you need new types
    if you want to restrict the set of possible variable values.
    """

    __slots__ = ()


    def set (self, value):
        """
        Set the current value for the variable.  As a result, ‘changed’ signal will be
        emitted, but only if the new value is not equal to the old one.  For derived types
        this method can raise C{ValueError} if the value doesn’t pass
        C{L{is_allowed_value}} test.

        @param  value:      new value for the variable.
        @type   value:      C{object}

        @rtype:             C{bool}
        @returns:           Whether variable value changed as a result.

        @raises ValueError: if C{value} is not acceptable according to
                            C{L{is_allowed_value}}.
        """

        return self._set (value)



class WatcherVariable (AbstractValueTrackingVariable):

    """
    A variable that has changeable I{watched variable} and always has a value that matches
    that variable’s one.

    While it may seem redundant, watcher variables are convenient at times.  Instead of
    disconnecting your handler(s) from one variable’s ‘changed’ signal and connecting to
    another, you can create a proxy watcher variable and connect the handlers to its
    signal instead.  This is practically the same, but changing watched variable is one
    operation, while reconnecting handlers to a different variable is 2 × (number of
    handlers) ones.  Another advantage of a watcher is that when you change watched
    variable from A to B and those have different values, watcher’s ‘changed’ signal will
    get emitted.  With manual reconnecting you’d need to track that case specially.

    Watcher variable that doesn’t watch anything at the moment always has value of
    C{None}.

    @see:  condition.WatcherCondition
    """

    __slots__ = ('__watched_variable')


    def __init__(self, variable_to_watch = None):
        """
        Create a new watcher variable, watching C{variable_to_watch} initially.  The only
        argument is optional and can be omitted or set to C{None}.

        @raises TypeError:  if C{variable_to_watch} is not an instance of
                            C{L{AbstractVariable}} and not C{None}.
        @raises ValueError: if C{variable_to_watch} is this variable.

        @see:               C{L{watch}}
        """

        super (WatcherVariable, self).__init__(None)

        self.__watched_variable = None
        self.watch (variable_to_watch)


    def watch (self, variable_to_watch):
        """
        Watch C{variable_to_watch} instead of whatever is watched now.  This method
        disconnects internal handler from the old variable and connects it to the new one,
        if new is not C{None}.  Watching a different variable might change own state, in
        which case ‘changed’ signal will get emitted.

        @param  variable_to_watch: new variable to watch (copy value.)
        @type   variable_to_watch: C{L{AbstractVariable}} or C{None}

        @rtype:                    C{bool}
        @returns:                  Whether self value has changed as a result.

        @raises TypeError:         if C{variable_to_watch} is not an instance of
                                   C{L{AbstractVariable}} and not C{None}.
        @raises ValueError:        if C{variable_to_watch} is this variable.
        """

        if variable_to_watch is not None:
            if isinstance (variable_to_watch, AbstractVariable):
                if variable_to_watch is self:
                    raise ValueError ('cannot watch self')
            else:
                raise TypeError ('can only watch other variables')

        watched_variable = self.__get_watched_variable ()

        if watched_variable is variable_to_watch:
            return False

        old_value = self.get ()

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

        return self.get () != old_value


    def __get_watched_variable (self):
        if self.__watched_variable is not None:
            return self.__watched_variable ()
        else:
            return None


    watched_variable = property (__get_watched_variable,
                                 lambda self, variable: self.watch (variable),
                                 doc = ("""
                                        The currently watched variable or C{None} if
                                        nothing is being watched.  Setting this property
                                        is identical to calling C{L{watch}}; this
                                        duplication of functionality is intentional, since
                                        you cannot perform assignments in lambda
                                        functions.

                                        @type:  C{L{AbstractVariable}} or C{None}
                                        """))


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


    def _generate_derived_type_dictionary (cls, options):
        raise TypeError ("'WatcherVariable' doesn't support derive_type() method")

    _generate_derived_type_dictionary = classmethod (_generate_derived_type_dictionary)



#-- Internal variable classes -----------------------------------------

# FIXME: There is code duplication in these classes.  Use multiple inheritance?

class _PredicateOverVariable (AbstractStateTrackingCondition):

    __slots__ = ('__predicate', '__variable')


    def __init__(self, predicate, variable):
        if not is_callable (predicate):
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
                + super (_PredicateOverVariable, self)._additional_description (formatter))



class _VariableTransformation (AbstractValueTrackingVariable):

    __slots__ = ('__transformer', '__variable')


    def __init__(self, transformer, variable):
        if not is_callable (transformer):
            raise TypeError ('transformer must be callable')

        super (_VariableTransformation, self).__init__(transformer (variable.get ()))

        self.__transformer = transformer
        self.__variable    = weakref.ref (variable, self.__on_usage_change)

        variable.changed.connect (self.__update)


    def __get_variable (self):
        return self.__variable ()


    def __update (self, new_value):
        self._set (self.__transformer (new_value))


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
        return (['transformer: %s' % formatter (self.__transformer),
                 'variable: %s'  % formatter (self.__get_variable ())]
                + super (_VariableTransformation, self)._additional_description (formatter))



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
