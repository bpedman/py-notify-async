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
L{Conditions <AbstractCondition>} are boolean variables with attached L{signal
<AbstractSignal>} that is emitted when condition state changes.

G{classtree AbstractCondition}
"""

__docformat__ = 'epytext en'
__all__       = ('AbstractCondition', 'AbstractStateTrackingCondition',
                 'Condition', 'PredicateCondition', 'WatcherCondition')


import sys
import weakref

from notify.base   import AbstractValueObject
from notify.gc     import AbstractGCProtector
from notify.signal import CleanSignal
from notify.utils  import execute, is_callable, raise_not_implemented_exception, DummyReference



#-- Base condition class ---------------------------------------------

class AbstractCondition (AbstractValueObject):

    """
    Abstract base class of condition hierarchy tree.  All conditions derive from this
    class, so you should use C{isinstance (..., AbstractCondition)}, not
    C{isinstance (..., Condition)}.

    @cvar TRUE:
    A condition that is always true and never changes its state.

    @cvar FALSE:
    A condition that is always false and never changes its state.
    """

    __slots__ = ()


    # We won't use it internally for marginal optimization.
    state = property (lambda self: self.get (), lambda self, state: self.set (state),
                      doc = ("""
                             The current state of the condition.  This property is
                             writable, but setting it for immutable conditions will raise
                             C{NotImplementedError}.

                             @type: bool
                             """))


    def to_constant (state):
        """
        Return either C{L{TRUE}} or C{L{FALSE}}, depending on C{state} argument.  In other
        words, this static method returns a condition which is either always true or
        always false.

        @param state: desired state of the returned condition (coerced to C{bool} first.)
        @type  state: C{object}

        @rtype:       C{AbstractCondition}
        """

        if state:
            return AbstractCondition.TRUE
        else:
            return AbstractCondition.FALSE

    to_constant = staticmethod (to_constant)


    def __nonzero__(self):
        """
        Return the state of the condition.  Return value is the same as that of
        C{L{state}} property or C{L{get}} method.  Existance of C{__nonzero__} method
        simplifies condition usage in C{if}-like statements.

        @rtype:   C{bool}
        @returns: State of the condition.
        """

        return self.get ()

    if sys.version_info[0] >= 3:
        __bool__ = __nonzero__
        del __nonzero__


    def __invert__(self):
        """
        Return a condition, whose state is always the negation of this condition’s state.

        You don’t need this if you just want to test condition state: both
        C{not condition} and C{~condition} have the same logical value, but former doesn’t
        involve object creation.  However, the returned object has its own ‘changed’
        signal.  So, you should use this method if you need a I{trackable} condition, not
        one-time value.

        @note:
        There is no guarantee on the returned object except as noted above about its state
        and that it is an instance of C{AbstractCondition} or a subclass.  In particular,
        the returned object may or may not be identical to an existing one.

        @rtype: C{AbstractCondition}
        """

        return _Not (self)


    def __and__(self, other):
        """
        Return a condition, whose state is always logical ‘and’ function of this condition
        state and C{other} state.

        You don’t need this if you just want to test condition state: both
        C{condition1 and condition2} and C{condition1 & condition2} have the same logical
        value, but former doesn’t involve object creation.  However, the returned object
        has its own ‘changed’ signal.  So, you should use this method if you need a
        I{trackable} condition, not one-time value.

        @note:
        There is no guarantee on the returned object except as noted above about its state
        and that it is an instance of C{AbstractCondition} or a subclass.  In particular,
        the returned object may or may not be identical to an existing one.

        @rtype: C{AbstractCondition}
        """

        if isinstance (other, AbstractCondition):
            # Note: similar checks for `self' are performed in appropriate classes.

            if not (other is AbstractCondition.TRUE or other is AbstractCondition.FALSE):
                return _And (self, other)
            else:
                if other is AbstractCondition.TRUE:
                    return self
                else:
                    return other
        else:
            return NotImplemented


    def __or__(self, other):
        """
        Return a condition, whose state is always logical ‘or’ function of this condition
        state and C{other} state.

        You don’t need this if you just want to test condition state: both
        C{condition1 or condition2} and C{condition1 | condition2} have the same logical
        value, but former doesn’t involve object creation.  However, the returned object
        has its own ‘changed’ signal.  So, you should use this method if you need a
        I{trackable} condition, not one-time value.

        @note:
        There is no guarantee on the returned object except as noted above about its state
        and that it is an instance of C{AbstractCondition} or a subclass.  In particular,
        the returned object may or may not be identical to an existing one.

        @rtype: C{AbstractCondition}
        """

        if isinstance (other, AbstractCondition):
            # Note: similar checks for `self' are performed in appropriate classes.

            if not (other is AbstractCondition.TRUE or other is AbstractCondition.FALSE):
                return _Or (self, other)
            else:
                if other is AbstractCondition.TRUE:
                    return other
                else:
                    return self
        else:
            return NotImplemented


    def __xor__(self, other):
        """
        Return a condition, whose state is always logical ‘xor’ function of this condition
        state and C{other} state.

        The returned object has its own ‘changed’ signal, so primary use of this method is
        to receive a I{trackable} condition, not one-time value.  However, since there is
        no logical ‘xor’ function in Python, you may use it to compute a one-time value,
        though it is not efficient.

        @note:
        There is no guarantee on the returned object except as noted above about its state
        and that it is an instance of C{AbstractCondition} or a subclass.  In particular,
        the returned object may or may not be identical to an existing one.

        @rtype: C{AbstractCondition}
        """

        if isinstance (other, AbstractCondition):
            # Note: similar checks for `self' are performed in appropriate classes.

            if not (other is AbstractCondition.TRUE or other is AbstractCondition.FALSE):
                return _Xor (self, other)
            else:
                if other is AbstractCondition.TRUE:
                    return _Not (self)
                else:
                    return self
        else:
            return NotImplemented


    def if_else (self, true_condition, false_condition):
        """
        Return a condition, whose state is always that of C{true_condition} or
        C{false_condition}, depending on this condition state.  In Python 2.5 it can be
        written like this:

            >>> (condition.if_else (true_condition, false_condition).state \\
            ...  = (true_condition.state if condition else false_condition.state))

        This will hold not only right after calling this method, but also later, even if
        any of the involved conditions’ state changes.

        You don’t need this if you just want to compute a logical expression value.
        However, the returned object has its own ‘changed’ signal.  So, you should use
        this method if you need a I{trackable} condition, not one-time value.

        @note:
        There is no guarantee on the returned object except as noted above about its state
        and that it is an instance of C{AbstractCondition} or a subclass.  In particular,
        the returned object may or may not be identical to an existing one.

        @rtype: C{AbstractCondition}
        """

        if  (   isinstance (true_condition,  AbstractCondition)
             and isinstance (false_condition, AbstractCondition)):
            if true_condition is not false_condition:
                return _IfElse (self, true_condition, false_condition)
            else:
                return true_condition
        else:
            raise TypeError ("'true_condition' and 'false_condition' must be conditions")



class AbstractStateTrackingCondition (AbstractCondition):

    """
    A condition that stores its state (explicitly) instead of recomputing it each time.
    Since there is no public way to alter condition’s state, this class is still abstract.
    For a generic mutable condition implementation, see C{L{Condition}} class.

    Not all standard condition classes derive from C{AbstractStateTrackingCondition}, some
    internal ones inherit C{L{AbstractCondition}} directly instead.
    """

    __slots__ = ('__state')


    def __init__(self, initial_state):
        """
        Initialize a new condition with specified C{initial_state}.  The state may be not
        C{True} or C{False}, but it will be converted to either of these two values with
        C{bool} standard function.

        @param initial_state: initial state for the new condition.
        @type  initial_state: C{object}
        """

        super (AbstractStateTrackingCondition, self).__init__()
        self.__state = bool (initial_state)


    def get (self):
        """
        Get the current state of the condition.  Since this condition type stores its
        state, this is the last value as passed to C{L{_set}} method internally, except it
        is always converted to either C{True} or C{False} using C{bool} function.

        @rtype: C{bool}
        """

        return self.__state

    def _set (self, value):
        """
        Set the state of the condition internally.  The C{value} parameter is first
        coerced to boolean state using C{bool} function, then checked equality with the
        current state.  So, this method does all that is needed for C{set} method of a
        mutable condition.

        This method I{must not} be used from outside.  For mutable conditions, use C{set}
        instead; immutable ones update their states through other means.

        @param  value: new value for the variable (coerced to boolean state
                       automatically.)
        @type   value: C{object}

        @rtype:        C{bool}
        @returns:      Whether condition state changed as a result.
        """

        # This seems to be a little faster than more generic _set() as in variable branch.
        # Only possible since there are just two possible states.
        if value:
            if not self.get ():
                self.__state = True
                return self._value_changed (True)
        else:
            if self.get ():
                self.__state = False
                return self._value_changed (False)

        return False


    def _generate_derived_type_dictionary (cls, options):
        for attribute in (super (AbstractStateTrackingCondition, cls)
                          ._generate_derived_type_dictionary (options)):
            if attribute[0] not in ('get', 'set'):
                yield attribute

        functions        = {}
        object           = options.get ('object')
        filtered_options = AbstractValueObject._filter_options (options, 'cls', 'getter', 'setter')

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
            if 'setter' in options:
                setter_statement = ('setter (%s, initial_state)'
                                    % AbstractValueObject._get_object (options))
            else:
                setter_statement = ''

            if object is not None:
                execute (('def __init__(self, %s, initial_state):\n'
                          '    cls.__init__(self, initial_state)\n'
                          '    %s = %s\n'
                          '    %s\n')
                         % (object, AbstractValueObject._get_object (options), object,
                            setter_statement),
                         filtered_options, functions)
            else:
                execute (('def __init__(self, initial_state):\n'
                          '    cls.__init__(self, initial_state)\n'
                          '    %s\n')
                         % setter_statement,
                         filtered_options, functions)

        if 'setter' in options:
            execute (('def _set (self, value):\n'
                      '    state = bool (value)\n'
                      '    if self.get () != state:\n'
                      '        setter (%s, state)\n'
                      '        self._AbstractStateTrackingCondition__state = state\n'
                      '        return self._value_changed (state)\n'
                      '    else:\n'
                      '        return False')
                     % AbstractValueObject._get_object (options),
                     filtered_options, functions)

            execute ('def set (self, value): return self._set (value)', functions)

        for function in functions.items ():
            yield function


    _generate_derived_type_dictionary = classmethod  (_generate_derived_type_dictionary)



#-- Standard non-abstract conditions ---------------------------------

class Condition (AbstractStateTrackingCondition):

    """
    Standard implementation of a mutable condition.  It is an all-purpose class suitable
    for almost any use.  In particular, you may not derive new condition types and just
    use mutable conditions everywhere.  Deriving new types is more ‘proper’ and can make
    difference if you have some code that differentiates between mutable and immutable
    conditions, but using this class is somewhat simpler.
    """

    __slots__ = ()


    def set (self, value):
        """
        Set the state of the condition to C{value}.  Value is first converted using
        C{bool} function, so it doesn’t need to be either C{True} or C{False}.

        @param value: new I{state} of the condition (parameter name is just kept the same
                      as in the base class.)
        @type  value: C{object}

        @rtype:       C{bool}
        @returns:     Whether condition state changed as a result.
        """

        return self._set (value)



class PredicateCondition (AbstractStateTrackingCondition):

    """
    An immutable condition class, instances of which have state determined by some
    predicate.  Instances of this class have no way to know when their state should be
    recomputed, so you need to actively C{L{update}} it.  For an automated way, see
    C{L{AbstractVariable.predicate <variable.AbstractVariable.predicate>}} method.

    Predicate conditions remember their state, so C{predicate} is called only from
    C{L{__init__}} and C{L{update}} methods.  They also don’t reference last value they
    were updated for.

    Advantage of using predicate conditions over all-purpose mutable ones and setting its
    state to the same predicate over different objects is encapsulation.  Predicate
    conditions remember the way to evaluate their state.
    """

    __slots__ = ('__predicate')


    def __init__(self, predicate, initial_object):
        """
        Initialize a new predicate conditon, setting its initial state to
        C{predicate (initial_object)}.  C{predicate} is stored to be invoked also on any
        subsequent calls to C{L{update}} method.  Return value of C{predicate} is always
        coerced using C{bool} function, so it needn’t return a boolean value.

        @param predicate:      a callable accepting one argument used to compute
                               condition’s state.

        @param initial_object: the value to be passed to C{predicate} to find initial
                               state.
        @type  initial_object: C{object}

        @raises exception:     whatever C{predicate} raises, if anything.
        """

        if not is_callable (predicate):
            raise TypeError ('predicate must be callable')

        super (PredicateCondition, self).__init__(predicate (initial_object))
        self.__predicate = predicate


    def update (self, object):
        """
        Recompute condition state for new C{object}.  This method invokes stored
        C{predicate} (as passed to C{L{__init__}}) to calculate new state.

        @param object:     the value to be passed to the condition’s predicate.
        @type  object:     C{object}

        @rtype:            C{bool}
        @returns:          Whether the state has changed as a result of recomputing.

        @raises exception: whatever C{predicate} raises, if anything.
        """

        return self._set (self.__predicate (object))


    def _additional_description (self, formatter):
        return (['predicate: %s' % formatter (self.__predicate)]
                + super (PredicateCondition, self)._additional_description (formatter))


    def _generate_derived_type_dictionary (cls, options):
        raise TypeError ("'PredicateCondition' doesn't support derive_type() method")

    _generate_derived_type_dictionary = classmethod (_generate_derived_type_dictionary)



class WatcherCondition (AbstractStateTrackingCondition):

    """
    A condition that has changeable I{watched condition} and always has a state that
    matches that condition’s one.

    While it may seem redundant, watcher conditions are convenient at times.  Instead of
    disconnecting your handler(s) from one condition’s ‘changed’ signal and connecting to
    another, you can create a proxy watcher condition and connect the handlers to its
    signal instead.  This is practically the same, but changing watched condition is one
    operation, while reconnecting handlers to a different condition is 2 × (number of
    handlers) ones.  Another advantage of a watcher is that when you change watched
    condition from A to B and those have different states, watcher’s ‘changed’ signal will
    get emitted.  With manual reconnecting you’d need to track that case specially.

    Watcher condition that doesn’t watch anything at the moment always has C{False} state.

    @see:  variable.WatcherVariable
    """


    __slots__ = ('__watched_condition')


    def __init__(self, condition_to_watch = None):
        """
        Create a new watcher condition, watching C{condition_to_watch} initially.  The
        only argument is optional and can be omitted or set to C{None}.

        @param  condition_to_watch: condition to watch (copy state) initially.
        @type   condition_to_watch: C{L{AbstractCondition}} or C{None}

        @raises TypeError:          if C{condition_to_watch} is not an instance of
                                    C{L{AbstractCondition}} and not C{None}.
        @raises ValueError:         if C{condition_to_watch} is this condition.

        @see:                       C{L{watch}}
        """

        super (WatcherCondition, self).__init__(False)

        self.__watched_condition = None
        self.watch (condition_to_watch)


    def watch (self, condition_to_watch):
        """
        Watch C{condition_to_watch} instead of whatever is watched now.  This method
        disconnects internal handler from the old condition and connects it to the new
        one, if new is not C{None}.  Watching a different condition might change own
        state, in which case ‘changed’ signal will get emitted.

        @param  condition_to_watch: new condition to watch (copy state.)
        @type   condition_to_watch: C{L{AbstractCondition}} or C{None}

        @rtype:                     C{bool}
        @returns:                   Whether self state has changed as a result.

        @raises TypeError:          if C{condition_to_watch} is not an instance of
                                    C{L{AbstractCondition}} and not C{None}.
        @raises ValueError:         if C{condition_to_watch} is this condition.
        """

        if condition_to_watch is not None:
            if isinstance (condition_to_watch, AbstractCondition):
                if condition_to_watch is self:
                    raise ValueError ('cannot watch self')
            else:
                raise TypeError ('can only watch other conditions')

        watched_condition = self.__get_watched_condition ()

        if watched_condition is condition_to_watch:
            return False

        old_state = self.get ()

        if watched_condition is not None:
            watched_condition.changed.disconnect (self._set)

        if condition_to_watch is not None:
            self.__watched_condition = weakref.ref (condition_to_watch, self.__on_usage_change)
            condition_to_watch.store (self._set)
        else:
            self.__watched_condition = None
            self._set (False)

        if self._has_signal ():
            if watched_condition is None and condition_to_watch is not None:
                AbstractGCProtector.default.protect (self)
            elif watched_condition is not None and condition_to_watch is None:
                AbstractGCProtector.default.unprotect (self)

        return self.get () != old_state


    def __get_watched_condition (self):
        if self.__watched_condition is not None:
            return self.__watched_condition ()
        else:
            return None


    watched_condition = property (__get_watched_condition,
                                  lambda self, condition: self.watch (condition),
                                  doc = ("""
                                         The currently watched condition or C{None} if
                                         nothing is being watched.  Setting this property
                                         is identical to calling C{L{watch}}; this
                                         duplication of functionality is intentional,
                                         since you cannot perform assignments in lambda
                                         functions.

                                         @type:  C{L{AbstractCondition}} or C{None}
                                         """))


    def _create_signal (self):
        if self.__get_watched_condition () is not None:
            AbstractGCProtector.default.protect (self)

        signal = CleanSignal (self)
        return signal, weakref.ref (signal, self.__on_usage_change)


    def __on_usage_change (self, object):
        # Complexities because watched condition can change and this function may be
        # called on previously watched condition.

        if self._remove_signal (object):
            if self.__get_watched_condition () is not None:
                AbstractGCProtector.default.unprotect (self)
        else:
            if object is self.__watched_condition:
                self.__watched_condition = None

                if self._has_signal ():
                    AbstractGCProtector.default.unprotect (self)


    def _additional_description (self, formatter):
        return (['watching %s' % formatter (self.__get_watched_condition ())]
                + super (WatcherCondition, self)._additional_description (formatter))


    def _generate_derived_type_dictionary (cls, options):
        raise TypeError ("'WatcherCondition' doesn't support derive_type() method")

    _generate_derived_type_dictionary = classmethod (_generate_derived_type_dictionary)



#-- Internal conditions ----------------------------------------------

class _True (AbstractCondition):

    __slots__ = ()


    def get (self):
        return True


    def __invert__(self):
        return AbstractCondition.FALSE


    def __and__(self, other):
        if isinstance (other, AbstractCondition):
            return other
        else:
            return NotImplemented


    def __or__(self, other):
        if isinstance (other, AbstractCondition):
            return self
        else:
            return NotImplemented


    def __xor__(self, other):
        if isinstance (other, AbstractCondition):
            return ~other
        else:
            return NotImplemented


    def if_else (self, true_condition, false_condition):
        if  (    isinstance (true_condition,  AbstractCondition)
             and isinstance (false_condition, AbstractCondition)):
            return true_condition
        else:
            raise TypeError ("'true_condition' and 'false_condition' must be conditions")


    def __repr__(self):
        # If you hack and use a different instance, it will not be proper.  But you
        # shouldn't anyway.
        return 'notify.condition.AbstractCondition.TRUE'

    def __str__(self):
        return 'Condition.TRUE'



class _False (AbstractCondition):

    __slots__ = ()


    def get (self):
        return False


    def __invert__(self):
        return AbstractCondition.TRUE


    def __and__(self, other):
        if isinstance (other, AbstractCondition):
            return self
        else:
            return NotImplemented


    def __or__(self, other):
        if isinstance (other, AbstractCondition):
            return other
        else:
            return NotImplemented


    def __xor__(self, other):
        if isinstance (other, AbstractCondition):
            return other
        else:
            return NotImplemented


    def if_else (self, true_condition, false_condition):
        if  (    isinstance (true_condition,  AbstractCondition)
             and isinstance (false_condition, AbstractCondition)):
            return false_condition
        else:
            raise TypeError ("'true_condition' and 'false_condition' must be conditions")


    def __repr__(self):
        # If you hack and use a different instance, it will not be proper.  But you
        # shouldn't anyway.
        return 'notify.condition.AbstractCondition.FALSE'

    def __str__(self):
        return 'Condition.FALSE'



AbstractCondition.TRUE  = _True ()
AbstractCondition.FALSE = _False ()



# Previously derived from `AbstractStateTrackingCondition', but this is a tiny little bit
# more efficient.

class _Not (AbstractCondition):

    # We need to save our state, since `negated_condition' may be gc-collected.
    __slots__ = ('__state', '__negated_condition')


    def __init__(self, negated_condition):
        super (_Not, self).__init__()

        self.__state             = not negated_condition
        self.__negated_condition = weakref.ref (negated_condition, self.__on_usage_change)

        negated_condition.changed.connect (self.__on_negated_condition_change)


    def get (self):
        return self.__state

    def __on_negated_condition_change (self, new_state):
        self.__state = not new_state
        self._value_changed (not new_state)


    def __get_negated_condition (self):
        negated_condition = self.__negated_condition ()

        if negated_condition is not None:
            return negated_condition
        else:
            return AbstractCondition.to_constant (self.__state)


    def _create_signal (self):
        if self.__negated_condition () is not None:
            AbstractGCProtector.default.protect (self)

        signal = CleanSignal (self)
        return signal, weakref.ref (signal, self.__on_usage_change)

    def __on_usage_change (self, object):
        self._remove_signal (object)

        if self._has_signal () or self.__negated_condition () is not None:
            AbstractGCProtector.default.unprotect (self)


    def _additional_description (self, formatter):
        return (['not %s' % formatter (self.__get_negated_condition ())]
                + super (_Not, self)._additional_description (formatter))


    def __invert__(self):
        return self.__get_negated_condition ()


    def __xor__(self, other):
        if not isinstance (other, _Not):
            return super (_Not, self).__xor__(other)
        else:
            return _Xor (self.__get_negated_condition (), other.__get_negated_condition ())


    def if_else (self, true_condition, false_condition):
        return self.__get_negated_condition ().if_else (false_condition, true_condition)



class _Binary (AbstractCondition):

    __slots__ = ('__condition1', '__condition2', '_term_state')


    def __init__(self, condition1, condition2):
        super (_Binary, self).__init__()

        on_usage_change   = self.__on_usage_change
        self.__condition1 = weakref.ref (condition1, on_usage_change)
        self.__condition2 = weakref.ref (condition2, on_usage_change)
        self._term_state  = condition1.get () + 2 * condition2.get ()

        condition1.changed.connect (self._on_term1_change)
        condition2.changed.connect (self._on_term2_change)


    # For efficiency reasons, descendants must override fully.
    def _on_term1_change (self, new_state):
        raise_not_implemented_exception (self)

    def _on_term2_change (self, new_state):
        raise_not_implemented_exception (self)


    def _create_signal (self):
        if (   isinstance (self.__condition1, weakref.ReferenceType)
            or isinstance (self.__condition2, weakref.ReferenceType)):
            AbstractGCProtector.default.protect (self)

        signal = CleanSignal (self)
        return signal, weakref.ref (signal, self.__on_usage_change)


    def __on_usage_change (self, object):
        if self._remove_signal (object):
            if (   isinstance (self.__condition1, weakref.ReferenceType)
                or isinstance (self.__condition2, weakref.ReferenceType)):
                AbstractGCProtector.default.unprotect (self)
        else:
            if object is self.__condition1:
                self.__condition1 = _get_dummy_reference (self._term_state & 1)
                if self._has_signal () and isinstance (self.__condition2, DummyReference):
                    AbstractGCProtector.default.unprotect (self)
            else:
                self.__condition2 = _get_dummy_reference (self._term_state & 2)
                if self._has_signal () and isinstance (self.__condition1, DummyReference):
                    AbstractGCProtector.default.unprotect (self)


    def _get_operator_name (self):
        raise_not_implemented_exception (self)

    def __repr__(self):
        return '<%s: %r %s %r>' % (self.get (),
                                   self.__condition1 (),
                                   self._get_operator_name (),
                                   self.__condition2 ())

    def __str__(self):
        return '<%s: %s %s %s>' % (self.get (),
                                   self.__condition1 (),
                                   self._get_operator_name (),
                                   self.__condition2 ())



class _And (_Binary):

    __slots__ = ()


    def get (self):
        return self._term_state == 3


    def _on_term1_change (self, new_state):
        self._term_state ^= 1
        if self._term_state & 2:
            self._value_changed (new_state)

    def _on_term2_change (self, new_state):
        self._term_state ^= 2
        if self._term_state & 1:
            self._value_changed (new_state)


    def _get_operator_name (self):
        return 'and'



class _Or (_Binary):

    __slots__ = ()


    def get (self):
        return self._term_state != 0


    def _on_term1_change (self, new_state):
        self._term_state ^= 1
        if not self._term_state & 2:
            self._value_changed (new_state)

    def _on_term2_change (self, new_state):
        self._term_state ^= 2
        if not self._term_state & 1:
            self._value_changed (new_state)


    def _get_operator_name (self):
        return 'or'



class _Xor (_Binary):

    __slots__ = ()


    def get (self):
        return self._term_state == 1 or self._term_state == 2


    def _on_term1_change (self, new_state):
        self._term_state ^= 1
        self._value_changed (self._term_state == 1 or self._term_state == 2)

    def _on_term2_change (self, new_state):
        self._term_state ^= 2
        self._value_changed (self._term_state == 1 or self._term_state == 2)


    def _get_operator_name (self):
        return 'xor'



# Implementation note: `self.__term_state' is computed by a peculiar formula and many
# functions depend on this way.  If you change the formula or `self.__term_state'
# otherwise, you need to make adjustments in many places.

class _IfElse (AbstractCondition):

    __slots__ = ('__if', '__then', '__else', '__term_state')


    __TERM_STATE_TO_SELF_STATE = (False, True, False, True, False, False, True, True)


    def __init__(self, _if, _then, _else):
        super (_IfElse, self).__init__()

        on_usage_change   = self.__on_usage_change
        self.__if         = weakref.ref (_if,   on_usage_change)
        self.__then       = weakref.ref (_then, on_usage_change)
        self.__else       = weakref.ref (_else, on_usage_change)
        self.__term_state = (_if.get () * 4 + _then.get () * 2 + _else.get ())

        _if  .changed.connect (self.__on_if_term_change)
        _then.changed.connect (self.__on_then_term_change)
        _else.changed.connect (self.__on_else_term_change)


    def get (self):
        return _IfElse.__TERM_STATE_TO_SELF_STATE[self.__term_state]


    def __on_if_term_change (self, new_state):
        self.__term_state ^= 4

        if self.__term_state & 3 == 1 or self.__term_state & 3 == 2:
            self._value_changed (self.__term_state == 1 or self.__term_state == 6)


    def __on_then_term_change (self, new_state):
        self.__term_state ^= 2

        if self.__term_state >= 4:
            self._value_changed (new_state)


    def __on_else_term_change (self, new_state):
        self.__term_state ^= 1

        if self.__term_state < 4:
            self._value_changed (new_state)


    def _create_signal (self):
        if (   isinstance (self.__if,   weakref.ReferenceType)
            or isinstance (self.__then, weakref.ReferenceType)
            or isinstance (self.__else, weakref.ReferenceType)):
            AbstractGCProtector.default.protect (self)

        signal = CleanSignal (self)
        return signal, weakref.ref (signal, self.__on_usage_change)


    def __on_usage_change (self, object):
        if self._remove_signal (object):
            if (   isinstance (self.__if,   weakref.ReferenceType)
                or isinstance (self.__then, weakref.ReferenceType)
                or isinstance (self.__else, weakref.ReferenceType)):
                AbstractGCProtector.default.unprotect (self)
        else:
            if object is self.__if:
                self.__if = _get_dummy_reference (self.__term_state & 4)
                if (self._has_signal ()
                    and isinstance (self.__then, DummyReference)
                    and isinstance (self.__else, DummyReference)):
                    AbstractGCProtector.default.unprotect (self)

            elif object is self.__then:
                self.__then = _get_dummy_reference (self.__term_state & 2)
                if (self._has_signal ()
                    and isinstance (self.__if,   DummyReference)
                    and isinstance (self.__else, DummyReference)):
                    AbstractGCProtector.default.unprotect (self)

            else:
                self.__else = _get_dummy_reference (self.__term_state & 1)
                if (self._has_signal ()
                    and isinstance (self.__if,   DummyReference)
                    and isinstance (self.__then, DummyReference)):
                    AbstractGCProtector.default.unprotect (self)


    def __invert__(self):
        # We don't create an object directly to include whatever optimizations might be
        # there in if_else() method of `self.__if()'.
        return self.__if ().if_else (self.__else (), self.__then ())


    def __repr__(self):
        return '<%r if %r else %r>' % (self.__then (), self.__if (), self.__else ())

    def __str__(self):
        return '<%s if %s else %s>' % (self.__then (), self.__if (), self.__else ())



_TRUE_REFERENCE  = DummyReference (AbstractCondition.TRUE)
_FALSE_REFERENCE = DummyReference (AbstractCondition.FALSE)



def _get_dummy_reference (is_true):
    if is_true:
        return _TRUE_REFERENCE
    else:
        return _FALSE_REFERENCE



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
