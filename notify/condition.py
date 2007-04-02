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
L{Conditions <AbstractCondition>} are boolean variables with attached L{signal
<AbstractSignal>} that is emitted when condition state changes.

G{classtree AbstractCondition}
"""

__docformat__ = 'epytext en'
__all__       = ('AbstractCondition', 'AbstractStateTrackingCondition',
                 'Condition', 'PredicateCondition', 'WatcherCondition')


import weakref

from notify.base   import *
from notify.gc     import *
from notify.signal import *
from notify.utils  import *



#-- Base condition class ---------------------------------------------

class AbstractCondition (AbstractValueObject):

    """
    Abstract base class of condition hierarchy tree.  All conditions derive from this
    class, so you should use C{isinstance (..., AbstractCondition)}, not
    C{isinstance (..., Condition)}.
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

        @rtype: AbstractCondition
        """

        if state:
            return AbstractCondition.TRUE
        else:
            return AbstractCondition.FALSE

    to_constant = staticmethod (to_constant)


    def __nonzero__(self):
        """
        Return the state of the condition.  Return value is the same as that of C{L{get}}
        method.  Existance of C{__nonzero__} method simplifies condition usage in
        C{if}-like statements.

        @rtype:   bool
        @returns: State of the condition.
        """

        return self.get ()


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

        @rtype: AbstractCondition
        """

        return _Not (self)


    def __and__(self, other):
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

        @rtype: AbstractCondition
        """

        if  (   isinstance (true_condition,  AbstractCondition)
             and isinstance (false_condition, AbstractCondition)):
            if true_condition is not false_condition:
                return _IfElse (self, true_condition, false_condition)
            else:
                return true_condition
        else:
            raise TypeError ("`true_condition' and `false_condition' must be conditions")



class AbstractStateTrackingCondition (AbstractCondition):

    """
    A condition that stores its state (explicitly) instead of recomputing it each time.
    Since there is no public way to alter condition’s state, this class is still abstract.
    For a generic mutable condition implementation, see C{L{Condition}} class.

    Not all standard condition classes derive from C{AbstractStateTrackingCondition}, some
    internal ones inherit C{L{AbstractCondition}} directly instead.
    """

    __slots__ = ('_AbstractStateTrackingCondition__state')


    def __init__(self, initial_state):
        """
        Initialize a new condition with specified C{initial_state}.  The state may be not
        C{True} or C{False}, but it will be converted to either of these two values with
        C{bool} standard function.
        """

        super (AbstractStateTrackingCondition, self).__init__()
        self.__state = bool (initial_state)


    def get (self):
        return self.__state

    def _set (self, value):
        state = bool (value)

        if self.get () is not state:
            self.__state = state
            return self._value_changed (state)
        else:
            return False


    def _generate_derived_type_dictionary (self_class, options):
        for attribute in (super (AbstractStateTrackingCondition, self_class)
                          ._generate_derived_type_dictionary (options)):
            if attribute[0] != 'get':
                yield attribute

        functions = {}
        object    = options.get ('object')

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
            if object is not None:
                exec (('def __init__(self, %s, initial_state):\n'
                       '    self_class.__init__(self, initial_state)\n'
                       '    %s = %s')
                      % (object, AbstractValueObject._get_object (options), object)) \
                      in options, functions
            else:
                exec ('def __init__(self, initial_state):\n'
                      '    self_class.__init__(self, initial_state)\n') in options, functions

        for function in functions.iteritems ():
            yield function

        del functions
        del object


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
        self._set (value)



class PredicateCondition (AbstractStateTrackingCondition):

    """
    An immutable condition class, instances of which have state determined by some
    predicate.  Instances of this class have no way to know when their state should be
    recomputed, so you need to actively C{L{update}} it.  For an automated way, see
    C{L{AbstractVariable.predicate <variable.AbstractVariable.predicate>}} method.

    Advantage of using predicate conditions over all-purpose mutable ones and setting its
    state to the same predicate over different objects is encapsulation.  Predicate
    conditions remember the way to evaluate their state.
    """

    __slots__ = ('_PredicateCondition__predicate')


    def __init__(self, predicate, initial_object):
        if not callable (predicate):
            raise TypeError ('predicate must be callable')

        super (PredicateCondition, self).__init__(predicate (initial_object))
        self.__predicate = predicate


    def update (self, object):
        self._set (self.__predicate (object))


    def _additional_description (self, formatter):
        return (['predicate: %s' % formatter (self.__predicate)]
                + super (PredicateCondition, self)._additional_description (formatter))



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

    Watcher condition that doesn’t watch anything at the moment always has state C{False}.

    @see:  variable.WatcherVariable
    """


    __slots__ = ('_WatcherCondition__watched_condition')


    def __init__(self, condition_to_watch = None):
        """
        Create a new wather condition, watching C{condition_to_watch} initially.  The only
        argument is optional and can be omitted or set to C{None}.
        """

        super (WatcherCondition, self).__init__(False)

        self.__watched_condition = None
        self.watch (condition_to_watch)


    def watch (self, condition_to_watch):
        if (condition_to_watch is not None
            and (   not isinstance (condition_to_watch, AbstractCondition)
                 or condition_to_watch is self)):
            raise TypeError ('can only watch other conditions')

        watched_condition = self.__get_watched_condition ()
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


    def __get_watched_condition (self):
        if self.__watched_condition is not None:
            return self.__watched_condition ()
        else:
            return None


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
            raise TypeError ("`true_condition' and `false_condition' must be conditions")


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
            raise TypeError ("`true_condition' and `false_condition' must be conditions")


    def __repr__(self):
        # If you hack and use a different instance, it will not be proper.  But you
        # shouldn't anyway.
        return 'notify.condition.AbstractCondition.FALSE'

    def __str__(self):
        return 'Condition.FALSE'



AbstractCondition.TRUE  = _True ()
AbstractCondition.FALSE = _False ()



class _Not (AbstractStateTrackingCondition):

    __slots__ = ('_Not__negated_condition')


    def __init__(self, negated_condition):
        super (_Not, self).__init__(not negated_condition)

        self.__negated_condition = weakref.ref (negated_condition, self.__on_usage_change)
        negated_condition.changed.connect (self.__on_negated_condition_change)


    def __on_negated_condition_change (self, new_state):
        self._set (not new_state)


    def __get_negated_condition (self):
        negated_condition = self.__negated_condition ()

        if negated_condition is not None:
            return negated_condition
        else:
            return AbstractCondition.to_constant (self.get ())


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

    __slots__ = ('_Binary__condition1', '_Binary__condition2', '_num_true_conditions')


    def __init__(self, condition1, condition2):
        super (_Binary, self).__init__()

        self.__condition1 = weakref.ref (condition1, self.__on_usage_change)
        self.__condition2 = weakref.ref (condition2, self.__on_usage_change)

        condition1.changed.connect (self._on_term_change)
        condition2.changed.connect (self._on_term_change)

        # Note: this doesn't allow for non-symmetric condition implementation, but we
        # don't need those anyway and this class is private.
        self._num_true_conditions = condition1.get () + condition2.get ()


    # For efficiency reasons, descendants must override fully.
    def _on_term_change (self, new_state):
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
                self.__condition1 = _get_dummy_reference (self._num_true_conditions
                                                          - self.__condition2 ().get ())
                if self._has_signal () and isinstance (self.__condition2, DummyReference):
                    AbstractGCProtector.default.unprotect (self)
            else:
                self.__condition2 = _get_dummy_reference (self._num_true_conditions
                                                          - self.__condition1 ().get ())
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
        return self._num_true_conditions == 2

    def _on_term_change (self, new_state):
        if new_state:
            self._num_true_conditions += 1
            if self._num_true_conditions == 2:
                self._value_changed (True)
        else:
            self._num_true_conditions -= 1
            if self._num_true_conditions == 1:
                self._value_changed (False)


    def _get_operator_name (self):
        return 'and'



class _Or (_Binary):

    __slots__ = ()


    def get (self):
        return self._num_true_conditions > 0

    def _on_term_change (self, new_state):
        if new_state:
            self._num_true_conditions += 1
            if self._num_true_conditions == 1:
                self._value_changed (True)
        else:
            self._num_true_conditions -= 1
            if self._num_true_conditions == 0:
                self._value_changed (False)


    def _get_operator_name (self):
        return 'or'



class _Xor (_Binary):

    __slots__ = ()


    def get (self):
        return self._num_true_conditions == 1

    def _on_term_change (self, new_state):
        if new_state:
            self._num_true_conditions += 1
        else:
            self._num_true_conditions -= 1

        self._value_changed (self._num_true_conditions == 1)


    def _get_operator_name (self):
        return 'xor'



class _IfElse (AbstractCondition):

    __slots__ = ('_IfElse__if', '_IfElse__then', '_IfElse__else', '_IfElse__term_state')


    __TERM_STATE_TO_SELF_STATE = (False, True, False, True, False, False, True, True)


    def __init__(self, _if, _then, _else):
        super (_IfElse, self).__init__()

        self.__if         = weakref.ref (_if,   self.__on_usage_change)
        self.__then       = weakref.ref (_then, self.__on_usage_change)
        self.__else       = weakref.ref (_else, self.__on_usage_change)
        self.__term_state = (_if.get () * 4 + _then.get () * 2 + _else.get ())

        _if  .changed.connect (self.__on_term_change)
        _then.changed.connect (self.__on_term_change)
        _else.changed.connect (self.__on_term_change)


    def get (self):
        return _IfElse.__TERM_STATE_TO_SELF_STATE[self.__term_state]


    def __on_term_change (self, new_state):
        # FIXME: Is it efficient enough?
        old_state         = _IfElse.__TERM_STATE_TO_SELF_STATE[self.__term_state]
        self.__term_state = (  self.__if   ().get () * 4
                             + self.__then ().get () * 2
                             + self.__else ().get ())
        new_state         = _IfElse.__TERM_STATE_TO_SELF_STATE[self.__term_state]

        if  new_state != old_state:
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


    def __repr__(self):
        return '<%r if %r else %r>' % (self.__then, self.__if, self.__else)

    def __str__(self):
        return '<%s if %s else %s>' % (self.__then, self.__if, self.__else)



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
