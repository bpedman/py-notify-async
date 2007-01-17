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
from notify.signal import *
from notify.utils  import *



#-- Base condition class ---------------------------------------------

class AbstractCondition (AbstractValueObject):

    __slots__ = ()


    # We won't use it internally for marginal optimization.
    state = property (lambda self: self.get (), lambda self, state: self.set (state))


    def to_constant (state):
        if state:
            return AbstractCondition.TRUE
        else:
            return AbstractCondition.FALSE

    to_constant = staticmethod (to_constant)


    def __nonzero__(self):
        return self.get ()


    def __invert__(self):
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
            raise TypeError ('can only conjunct with other conditions')


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
            raise TypeError ('can only disjunct with other conditions')


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
            raise TypeError ('can only xor with other conditions')


    def ifelse (self, true_condition, false_condition):
        if  (   isinstance (true_condition,  AbstractCondition)
             and isinstance (false_condition, AbstractCondition)):
            if true_condition is not false_condition:
                return _IfElse (self, true_condition, false_condition)
            else:
                return true_condition
        else:
            raise TypeError ("`true_condition' and `false_condition' must be conditions")



class AbstractStateTrackingCondition (AbstractCondition):

    __slots__ = ('_AbstractStateTrackingCondition__state')


    def __init__(self, initial_state):
        super (AbstractStateTrackingCondition, self).__init__()
        self.__state = bool (initial_state)


    def get (self):
        return self.__state

    def _set (self, value):
        state = bool (value)

        if self.get () is not state:
            self.__state = state
            return self._changed (state)
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
                       '    self_class.__init__ (self, getter (%s))\n'
                       '    %s = %s')
                      % (object, object, AbstractValueObject._get_object (options), object)) \
                      in options, functions
            else:
                exec ('def __init__(self):\n'
                      '    self_class.__init__ (self, getter (self))\n') in options, functions

            exec (('def resynchronize_with_backend (self):\n'
                   '    self._set (getter (%s))')
                  % AbstractValueObject._get_object (options)) in options, functions

        else:
            if object is not None:
                exec (('def __init__(self, %s, initial_state):\n'
                       '    self_class.__init__ (self, initial_state)\n'
                       '    %s = %s')
                      % (object, AbstractValueObject._get_object (options), object)) \
                      in options, functions
            else:
                exec ('def __init__(self, initial_state):\n'
                      '    self_class.__init__ (self, initial_state)\n') in options, functions

        for function in functions.iteritems ():
            yield function

        del functions
        del object


    _generate_derived_type_dictionary = classmethod  (_generate_derived_type_dictionary)



#-- Standard non-abstract conditions ---------------------------------

class Condition (AbstractStateTrackingCondition):

    __slots__ = ()


    def set (self, value):
        self._set (value)



class PredicateCondition (AbstractStateTrackingCondition):

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

    __slots__ = ('_WatcherCondition__watched_condition')


    def __init__(self, condition_to_watch = None):
        super (WatcherCondition, self).__init__(False)

        self.__watched_condition = None
        self.watch (condition_to_watch)


    def watch (self, condition_to_watch):
        if (condition_to_watch is not None
            and isinstance (condition_to_watch, AbstractCondition)
            and condition_to_watch is not self):
            raise TypeError ('can only watch other conditions')

        watched_condition = self.__get_watched_condition ()
        if watched_condition is not None:
            watched_condition.signal_changed ().disconnect (self._set)

        if condition_to_watch is not None:
            self.__watched_condition = weakref.ref (condition_to_watch, self.__on_usage_change)
            condition_to_watch.store (self._set)
        else:
            self.__watched_condition = None
            self._set (False)

        if self._has_signal ():
            if watched_condition is None and condition_to_watch is not None:
                mark_object_as_used (self)
            elif watched_condition is not None and condition_to_watch is None:
                mark_object_as_unused (self)


    def __get_watched_condition (self):
        if self.__watched_condition is not None:
            return self.__watched_condition ()
        else:
            return None


    def _create_signal (self):
        if self.__get_watched_condition () is not None:
            mark_object_as_used (self)

        signal = CleanSignal ()
        return signal, weakref.ref (signal, self.__on_usage_change)


    def __on_usage_change (self, object):
        # Complexities because watched condition can change and this function may be
        # called on previously watched condition.

        if self._remove_signal (object):
            if self.__get_watched_condition () is not None:
                mark_object_as_unused (self)
        else:
            if object is self.__watched_condition:
                self.__watched_condition = None

                if self._has_signal ():
                    mark_object_as_unused (self)


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
            raise TypeError ('can only conjunct with other conditions')


    def __or__(self, other):
        if isinstance (other, AbstractCondition):
            return self
        else:
            raise TypeError ('can only disjunct with other conditions')


    def __xor__(self, other):
        if isinstance (other, AbstractCondition):
            return ~other
        else:
            raise TypeError ('can only xor with other conditions')


    def ifelse (self, true_condition, false_condition):
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
            raise TypeError ('can only conjunct with other conditions')


    def __or__(self, other):
        if isinstance (other, AbstractCondition):
            return other
        else:
            raise TypeError ('can only disjunct with other conditions')


    def __xor__(self, other):
        if isinstance (other, AbstractCondition):
            return other
        else:
            raise TypeError ('can only xor with other conditions')


    def ifelse (self, true_condition, false_condition):
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
        negated_condition.signal_changed ().connect (self.__on_negated_condition_change)


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
            mark_object_as_used (self)

        signal = CleanSignal ()
        return signal, weakref.ref (signal, self.__on_usage_change)

    def __on_usage_change (self, object):
        self._remove_signal (object)

        if self._has_signal () or self.__negated_condition () is not None:
            mark_object_as_unused (self)


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


    def ifelse (self, true_condition, false_condition):
        return self.__get_negated_condition ().ifelse (false_condition, true_condition)



class _Binary (AbstractCondition):

    __slots__ = ('_Binary__condition1', '_Binary__condition2', '_num_true_conditions')


    def __init__(self, condition1, condition2):
        super (_Binary, self).__init__()

        self.__condition1 = weakref.ref (condition1, self.__on_usage_change)
        self.__condition2 = weakref.ref (condition2, self.__on_usage_change)

        condition1.signal_changed ().connect (self._on_term_change)
        condition2.signal_changed ().connect (self._on_term_change)

        # Note: this doesn't allow for non-symmetric condition implementation, but we
        # don't need those anyway and this class is private.
        self._num_true_conditions = condition1.get () + condition2.get ()


    # For efficiency reasons, descendants must override fully.
    def _on_term_change (self, new_state):
        raise_not_implemented_exception (self)


    def _create_signal (self):
        if (   isinstance (self.__condition1, weakref.ReferenceType)
            or isinstance (self.__condition2, weakref.ReferenceType)):
            mark_object_as_used (self)

        signal = CleanSignal ()
        return signal, weakref.ref (signal, self.__on_usage_change)


    def __on_usage_change (self, object):
        if self._remove_signal (object):
            if (   isinstance (self.__condition1, weakref.ReferenceType)
                or isinstance (self.__condition2, weakref.ReferenceType)):
                mark_object_as_unused (self)
        else:
            if object is self.__condition1:
                self.__condition1 = _get_dummy_reference (self._num_true_conditions
                                                          - self.__condition2 ().get ())
                if self._has_signal () and isinstance (self.__condition2, _DummyReference):
                    mark_object_as_unused (self)
            else:
                self.__condition2 = _get_dummy_reference (self._num_true_conditions
                                                          - self.__condition1 ().get ())
                if self._has_signal () and isinstance (self.__condition1, _DummyReference):
                    mark_object_as_unused (self)


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
                self._changed (True)
        else:
            self._num_true_conditions -= 1
            if self._num_true_conditions == 1:
                self._changed (False)


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
                self._changed (True)
        else:
            self._num_true_conditions -= 1
            if self._num_true_conditions == 0:
                self._changed (False)


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

        self._changed (self._num_true_conditions == 1)


    def _get_operator_name (self):
        return 'xor'



class _IfElse (AbstractCondition):

    __slots__ = ('_IfElse__if', '_IfElse__then', '_IfElse__else', '_IfElse__term_state')


    __TERM_STATE_TO_SELF_STATE = (False, True, False, True, False, False, True, True)


    def __init__(self, _if, _then, _else):
        super (_IfElse, self).__init__ ()

        self.__if         = weakref.ref (_if,   self.__on_usage_change)
        self.__then       = weakref.ref (_then, self.__on_usage_change)
        self.__else       = weakref.ref (_else, self.__on_usage_change)
        self.__term_state = (_if.get () * 4 + _then.get () * 2 + _else.get ())

        _if  .signal_changed ().connect (self.__on_term_change)
        _then.signal_changed ().connect (self.__on_term_change)
        _else.signal_changed ().connect (self.__on_term_change)


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
            self._changed (new_state)


    def _create_signal (self):
        if (   isinstance (self.__if,   weakref.ReferenceType)
            or isinstance (self.__then, weakref.ReferenceType)
            or isinstance (self.__else, weakref.ReferenceType)):
            mark_object_as_used (self)

        signal = CleanSignal ()
        return signal, weakref.ref (signal, self.__on_usage_change)


    def __on_usage_change (self, object):
        if self._remove_signal (object):
            if (   isinstance (self.__if,   weakref.ReferenceType)
                or isinstance (self.__then, weakref.ReferenceType)
                or isinstance (self.__else, weakref.ReferenceType)):
                mark_object_as_unused (self)
        else:
            if object is self.__if:
                self.__if = _get_dummy_reference (self.__term_state & 4)
                if (self._has_signal ()
                    and isinstance (self.__then, _DummyReference)
                    and isinstance (self.__else, _DummyReference)):
                    mark_object_as_unused (self)

            elif object is self.__then:
                self.__then = _get_dummy_reference (self.__term_state & 2)
                if (self._has_signal ()
                    and isinstance (self.__if,   _DummyReference)
                    and isinstance (self.__else, _DummyReference)):
                    mark_object_as_unused (self)

            else:
                self.__else = _get_dummy_reference (self.__term_state & 1)
                if (self._has_signal ()
                    and isinstance (self.__if,   _DummyReference)
                    and isinstance (self.__then, _DummyReference)):
                    mark_object_as_unused (self)


    def __repr__(self):
        return '<%r if %r else %r>' % (self.__then, self.__if, self.__else)

    def __str__(self):
        return '<%s if %s else %s>' % (self.__then, self.__if, self.__else)



class _DummyReference (object):

    __slots__ = ('_DummyReference__object')


    def __init__ (self, object):
        self.__object = object

    def __call__ (self):
        return self.__object


_TRUE_REFERENCE  = _DummyReference (AbstractCondition.TRUE)
_FALSE_REFERENCE = _DummyReference (AbstractCondition.FALSE)



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
