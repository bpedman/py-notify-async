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
Mostly internal module that contains functionality common to L{conditions <condition>} and
L{variables <variable>}.  You can use C{L{AbstractValueObject}} class directly, if really
needed, but almost always conditions or variables is what you need.
"""

__docformat__ = 'epytext en'
__all__       = ('AbstractValueObject',)


import sys

from notify.mediator import AbstractMediator
from notify.signal   import AbstractSignal, Signal
from notify.utils    import execute, is_callable, is_valid_identifier, mangle_identifier, \
                            raise_not_implemented_exception, StringType
 
try:
    import contextlib
except ImportError:
    # Ignore, related features will not be provided.
    pass



#-- Base class for conditions and variables --------------------------

class AbstractValueObject (object):

    """
    Base class for C{L{AbstractCondition <condition.AbstractCondition>}} and
    C{L{AbstractVariable <variable.AbstractVariable>}} implementing common functionality.

    @group Basic:
    get, set, mutable, changed

    @group Storing Using Handlers:
    store, store_safe, storing, storing_safely

    @group Synchronizing Two Objects:
    synchronize, synchronize_safe, desynchronize, desynchronize_fully, synchronizing,
    synchronizing_safely

    @group Freezing Value Changes:
    is_frozen, changes_frozen, with_changes_frozen

    @group Methods for Subclasses:
    _is_mutable, _value_changed, _create_signal, _has_signal, _remove_signal,
    _additional_description

    @group Internals:
    __get_changed_signal, __to_string, __flags, __signal

    @sort:
    get, set, mutable, changed,
    store, store_safe, storing, storing_safely,
    synchronize, synchronize_safe, desynchronize, desynchronize_fully, synchronizing,
    synchronizing_safely,
    is_frozen, changes_frozen, with_changes_frozen,
    _is_mutable, _value_changed, _create_signal, _has_signal, _remove_signal,
    _additional_description
    """

    __slots__ = ('__weakref__', '__signal', '__flags')


    # Implementation note: `__flags' are a sum of following values:
    # * 0 if there is no signal, 1 if `__signal' is an `AbstractSignal' instance, 2 if it
    #   is a reference to one;
    # * 0 if the object is not frozen, -4 if it is.
    #
    # The reason for the first term is to save one (slow) isinstance() call per `changed'
    # emission.  The second term is actually needed anyway, it is only `weird', since we
    # need to combine with the first.
    #
    # We rely on Python's caching of small integers, otherwise this does waste memory.


    def __init__(self):
        """
        Initialize new C{L{AbstractValueObject}}.  Base class only has (internal) field
        for ‘changed’ signal.  You may assume that the signal is only created when
        C{L{changed}} property is read for the first time.
        """

        super (AbstractValueObject, self).__init__()

        # For optimization reasons, `__signal' is created only when it is needed for the
        # first time.  This may improve memory consumption if there are many unused
        # properties.
        self.__signal = None
        self.__flags  = 0


    def get (self):
        """
        Get the current value of the object.  Note that the default implementation just
        raises C{NotImplementedError}, since the current value is not stored by default.

        @rtype: C{object}
        """

        raise_not_implemented_exception (self)

    def set (self, value):
        """
        Set the current value to C{value}, if possible.  Default implementation always
        raises C{NotImplementedError} as it is not mutable.

        @param value:                new value for C{AbstractValueObject}.

        @rtype:                      C{bool}
        @returns:                    Whether setting value had any effect, i.e. C{True}
                                     if C{value} is not equal to result of C{L{get}}
                                     method.

        @raises NotImplementedError: if the object is not mutable.
        @raises ValueError:          if C{value} is not suitable for some reason.
        """

        raise_not_implemented_exception (self)


    def _is_mutable (self):
        """
        Determine if object is mutable and thus if C{L{set}} method can be called at all.
        Default implementation assumes that if derived class overrides C{set} method, its
        instances are mutable.  This method should be overriden if that’s not the case.

        This method may be used from outside, but you should consider using C{L{mutable}}
        property instead, as it is public and more convenient.

        @rtype: C{bool}
        """

        return self.set.im_func is not AbstractValueObject.set.im_func

    if sys.version_info[0] >= 3:
        def temp (self):
            return self.set.__func__ is not AbstractValueObject.set

        temp.__doc__ = _is_mutable.__doc__
        _is_mutable  = temp
        del temp


    mutable = property (lambda self: self._is_mutable (),
                        doc = ("""
                               Read-only property indicating if this object is mutable.
                               In other words, if object’s value can be changed by
                               C{L{set}} method, or if it is computed by some means and
                               not settable from outside.

                               @type: bool
                               """))


    def __get_changed_signal (self):
        flags = self.__flags
        if flags & 3:
            if flags & 1:
                return self.__signal
            else:
                return self.__signal ()

        signal, self.__signal = self._create_signal ()
        if self.__signal is signal:
            self.__flags += 1
        else:
            self.__flags += 2

        return signal


    def _create_signal (self):
        """
        Create the signal that will be returned by C{L{changed}} property.  Default
        implementation returns an instance of C{L{Signal <signal.Signal>}} class without
        accumulator, but derived classes may wish to override this.

        Note that this method will be called only when getting C{changed} property and
        only if there is no signal yet.  I.e. only for the first reading at all or first
        reading after a call to C{L{_remove_signal}}.

        Return value of this method is a little bit tricky.  It must return a tuple of two
        objects, first being an instance of C{L{AbstractSignal}}.  The second object must
        be either the same signal object I{or} a reference to it, i.e. object with
        C{__call__} method returning the signal.  In the second case, you will most likely
        want to return a weak reference, but there is no restriction.

        @rtype:   C{L{AbstractSignal}}, C{object}
        @returns: See method description for details.
        """

        signal = Signal ()
        return signal, signal


    def _has_signal (self):
        """
        Determine if there is currently a ‘changed’ signal.  This is C{True} only if
        C{L{_create_signal}} has been called and the call to it was not followed by
        C{L{_remove_signal}}.

        This method I{can} be called from outside, but should normally be left to
        subclasses of C{AbstractValueObject}.

        @rtype: C{bool}
        """

        return self.__signal is not None

    def _remove_signal (self, signal):
        """
        Remove current ‘changed’ signal if it is the same object as specified by C{signal}
        argument.  If signal is removed, C{True} is returned.  Signal must only be removed
        if it has no handlers, to save memory, but it is allowed to call this method in
        other cases when its argument is guaranteed to be different from the ‘changed’
        signal.

        This function I{must not} be called from outside.  It is only for descendant
        classes’ use.

        @param  signal: the signal object or a reference to signal to remove (the same as
                        C{L{_create_signal}} returned.)

        @rtype:         C{bool}
        @returns:       Whether ‘changed’ signal is removed.
        """

        if self.__signal is signal:
            self.__signal  = None
            self.__flags  &= ~3
            return True
        else:
            return False


    def store (self, handler, *arguments, **keywords):
        """
        Make sure current value is ‘transmitted’ to C{handler} (with C{arguments}).  This
        means that the C{handler} is called once with the C{arguments} and the current
        value and afterwards each time the current value changes.  The only argument
        passed to C{handler} in addition to specified ones is the value as returned by the
        C{L{get}} method.

        See C{L{AbstractSignal.connect}} method description for details how C{arguments}
        are handled.

        @param  handler:   the object to store value with.
        @type   handler:   callable

        @param  arguments: optional arguments prepended to the current value when invoking
                           C{handler}.

        @raises TypeError: if C{handler} is not callable or cannot be called with
                           C{arguments} and current object value.
        """

        handler (*(arguments + (self.get (),)), **keywords)
        self.__get_changed_signal ().connect (handler, *arguments, **keywords)

    def store_safe (self, handler, *arguments, **keywords):
        """
        Like C{L{store}}, except that if C{handler} is already connected to this object’s
        ‘changed’ signal, this method does nothing.  See C{L{Signal.connect_safe}} method
        for details.

        @param  handler:   the object to store value with.
        @type   handler:   callable

        @param  arguments: optional arguments prepended to the current value when invoking
                           C{handler}.

        @rtype:            C{bool}
        @returns:          Whether C{handler} is connected to ‘changed’ signal.

        @raises TypeError: if C{handler} is not callable or cannot be called with
                           C{arguments} and current object value.
        """

        if not self.__get_changed_signal ().is_connected (handler, *arguments):
            handler (*(arguments + (self.get (),)), **keywords)
            self.__get_changed_signal ().connect (handler, *arguments, **keywords)

            return True

        else:
            return False


    def synchronize (self, value_object, mediator = None):
        """
        Synchronize own value with that of C{value_object}.  Both objects must be mutable.
        Value determined by C{value_object.get()} is first passed to C{self.set}.  After
        that, each object’s C{L{set}} method is connected to other object ‘changed’
        signal.  This guarantees that objects’ values remain the same if no exception
        occurs.  (Except that C{mediator}, if not C{None}, or either objects’ C{set}
        method can modify passed value.)

        If C{mediator} is not C{None}, values copied from C{value_object} to C{self} are
        passed through its ‘forward’ transformation, the way round—through ‘back’
        transformation.  See L{mediators description <mediator>} for details.

        @param  value_object: other value object to synchronize with.
        @type   value_object: C{AbstractValueObject}

        @param  mediator:     optional mediator to transform values between C{self} and
                              C{value_object}.
        @type   mediator:     C{L{AbstractMediator}} or C{None}

        @raises TypeError:    if C{value_object} is not an C{AbstractValueObject} or
                              C{mediator} is neither C{None} nor an instance of
                              C{L{AbstractMediator <mediator.AbstractMediator>}}.
        @raises ValueError:   if C{self} and C{value_object} are the same object.
        @raises ValueError:   if either C{self} or C{value_object} is not mutable.
        @raises ValueError:   if current value of C{value_object} is not suitable for
                              C{self}.
        """

        if not isinstance (value_object, AbstractValueObject):
            raise TypeError ("can only synchronize with other 'AbstractValueObject' instances")

        if value_object is self:
            raise ValueError ("can only synchronize with other 'AbstractValueObject' instances")

        if not self._is_mutable ():
            raise ValueError ("'%s' is not mutable" % self)

        if not value_object._is_mutable ():
            raise ValueError ("'%s' is not mutable" % value_object)

        if mediator is None:
            # Note: order is important!
            value_object.store (self.set)
            self.__get_changed_signal ().connect (value_object.set)

        else:
            if not isinstance (mediator, AbstractMediator):
                raise TypeError ('second argument must be a mediator')

            # Note: order is important!
            value_object.store (mediator.forward (self.set))
            self.__get_changed_signal ().connect (mediator.back (value_object.set))


    def synchronize_safe (self, value_object, mediator = None):
        """
        Like C{L{synchronize}} except that uses C{L{store_safe}} instead of L{store}.  See
        C{L{synchronize}} for details.

        @param  value_object: other value object to synchronize with.
        @type   value_object: C{AbstractValueObject}

        @param  mediator:     optional mediator to transform values between C{self} and
                              C{value_object}.
        @type   mediator:     C{L{AbstractMediator}} or C{None}

        @raises TypeError:    if C{value_object} is not an C{AbstractValueObject} or
                              C{mediator} is neither C{None} nor an instance of
                              C{L{AbstractMediator <mediator.AbstractMediator>}}.
        @raises ValueError:   if C{self} and C{value_object} are the same object.
        @raises ValueError:   if either C{self} or C{value_object} is not mutable.
        @raises ValueError:   if current value of C{value_object} is not suitable for
                              C{self}.
        """

        if not isinstance (value_object, AbstractValueObject):
            raise TypeError ("can only synchronize with other 'AbstractValueObject' instances")

        if value_object is self:
            raise ValueError ("can only synchronize with other 'AbstractValueObject' instances")

        if not value_object._is_mutable ():
            raise ValueError ("target 'AbstractValueObject' instance is not mutable")

        if mediator is None:
            # Note: order is important!
            value_object.store_safe (self.set)
            self.__get_changed_signal ().connect_safe (value_object.set)

        else:
            if not isinstance (mediator, AbstractMediator):
                raise TypeError ('second argument must be a mediator')

            # Note: order is important!
            value_object.store_safe (mediator.forward (self.set))
            self.__get_changed_signal ().connect_safe (mediator.back (value_object.set))


    def desynchronize (self, value_object, mediator = None):
        """
        Desynchronize own value with that of C{value_object}.  Note that values do not
        start to differ immediately, actually, this method doesn’t change values at all.
        Rather, values will not be synchronized anymore if any of the two changes.  If
        C{mediator} is not C{None}, this method cancels effect of a call to
        C{L{synchronize}} with the same or equal mediator only.

        Note that C{desynchronize} must be called the same number of times as
        C{synchronize} in order to cancel future synchronization.  If you need to do that
        in one call and regardless of how many times the latter has been called, use
        C{L{desynchronize_fully}} method instead.

        @param  value_object: other value object to desynchronize with.
        @type   value_object: C{AbstractValueObject}

        @param  mediator:     mediator, equal to what was passed to corresponding call
                              to C{L{synchronize}}.
        @type   mediator:     C{L{AbstractMediator}} or C{None}

        @rtype:               C{bool}
        @returns:             Whether C{self} and C{value_object} have been synchronized
                              before (using C{mediator} if it is not C{None}.)

        @raises TypeError:    if C{mediator} is neither C{None} nor an instance of
                              C{L{AbstractMediator <mediator.AbstractMediator>}}.

        @note:
        If C{L{set}} method of one of the values has been connected to other value’s
        ‘changed’ signal, but otherwise is not true, this method does nothing and returns
        C{False}.  So, it should be safe unless C{L{synchronize}} has been called or its
        effect has been emulated manually.
        """

        if mediator is not None and not isinstance (mediator, AbstractMediator):
            raise TypeError ('second argument must be a mediator')

        if (   not isinstance (value_object, AbstractValueObject)
            or not value_object._is_mutable ()
            or not self._has_signal ()
            or not value_object._has_signal ()):
            return False

        if mediator is None:
            forward = self.set
            back    = value_object.set
        else:
            forward = mediator.forward (self.set)
            back    = mediator.back    (value_object.set)

        if (    value_object.__get_changed_signal ().is_connected (forward)
            and self        .__get_changed_signal ().is_connected (back)):

            value_object.__get_changed_signal ().disconnect (forward)
            self.        __get_changed_signal ().disconnect (back)

            return True

        else:
            return False


    def desynchronize_fully (self, value_object, mediator = None):
        """
        Desynchronize own value with that of C{value_object}.  Note that values do not
        start to differ immediately, actually, this method doesn’t change values at all.
        Rather, values will not be synchronized anymore if any of the two changes.  If
        C{mediator} is not C{None}, this method cancels effect of a call to
        C{L{synchronize}} with the same or equal mediator only.

        Note that C{desynchronize_fully} cancels future synchronization regardless of how
        many times C{synchronize} has been called.  If that is not what you want, use
        C{L{desynchronize}} method instead.

        @param  value_object: other value object to desynchronize with.
        @type   value_object: C{AbstractValueObject}

        @param  mediator:     mediator, equal to what was passed to corresponding call
                              to C{L{synchronize}}.
        @type   mediator:     C{L{AbstractMediator}} or C{None}

        @rtype:               C{bool}
        @returns:             Whether C{self} and C{value_object} have been synchronized
                              before (using C{mediator} if it is not C{None}.)

        @raises TypeError:    if C{mediator} is neither C{None} nor an instance of
                              C{L{AbstractMediator <mediator.AbstractMediator>}}.

        @note:
        If C{L{set}} method of one of the values has been connected to other value’s
        ‘changed’ signal, but otherwise is not true, this method does nothing and returns
        C{False}.  So, it should be safe unless C{L{synchronize}} has been called or its
        effect has been emulated manually.

        Also remember that calling this function is not always the same as calling
        C{L{desynchronize}} until it starts to return C{False}.  These calls give
        different results if values’ C{set} methods are connected to other value’s
        ‘changed’ signal different number of times.  So, C{desynchronize_fully} may be
        dangerous at times.
        """

        if mediator is not None and not isinstance (mediator, AbstractMediator):
            raise TypeError ('second argument must be a mediator')

        if (   not isinstance (value_object, AbstractValueObject)
            or not value_object._is_mutable ()
            or not self._has_signal ()
            or not value_object._has_signal ()):
            return False

        if mediator is None:
            forward = self.set
            back    = value_object.set
        else:
            forward = mediator.forward (self.set)
            back    = mediator.back    (value_object.set)

        if (    value_object.__get_changed_signal ().is_connected (forward)
            and self        .__get_changed_signal ().is_connected (back)):

            value_object.__get_changed_signal ().disconnect_all (forward)
            self.        __get_changed_signal ().disconnect_all (back)

            return True

        else:
            return False
 
 
    if 'contextlib' in globals ():
        from notify._2_5 import base as _2_5

        storing                         = _2_5.storing
        storing_safely                  = _2_5.storing_safely
        synchronizing                   = _2_5.synchronizing
        synchronizing_safely            = _2_5.synchronizing_safely
        changes_frozen                  = _2_5.changes_frozen

        # This is needed so that Epydoc sees docstrings as UTF-8 encoded.
        storing.__module__              = __module__
        storing_safely.__module__       = __module__
        synchronizing.__module__        = __module__
        synchronizing_safely.__module__ = __module__
        changes_frozen.__module__       = __module__

        del _2_5


    def _value_changed (self, new_value):
        """
        Method that must be called every time object’s value changes.  Note that this
        method I{must not} be called from outside, it is for class descendants only.

        To follow general contract of the class, this method must be called only when the
        value indeed changes, i.e. when C{new_value} is not equal to C{self.get()}.
        C{_value_changed} itself does not check it and so this check (if needed) is up to
        implementing descendant class.

        For convenience, this method always returns C{True}.

        @param new_value: the new value of C{self}; will be also passed to ‘changed’
                          signal handlers.

        @rtype:           C{bool}
        @returns:         Always C{True}.
        """

        flags = self.__flags
        if flags == 1:
            self.__signal.emit (new_value)
        elif flags == 2:
            self.__signal ().emit (new_value)

        return True


    def is_frozen (self):
        """
        Determine if C{self}’s changes are currently frozen, i.e. if changing C{self}’s
        value will not emit ‘changed’ signal.  However, if the value is changed from the
        time the object is frozen to the time it is “thawed”, ‘changed’ signal will be
        emitted, once.

        @rtype: C{bool}

        @see:   C{L{with_changes_frozen}}
        @see:   C{L{changes_frozen}}
        """

        return self.__flags < 0


    def with_changes_frozen (self, callback, *arguments, **keywords):
        """
        Execute C{callback} with optional C{arguments}, freezing ‘changed’ signal of this
        object.  In other words, any changes to object’s value until C{callback} returns
        don’t cause emission of ‘changed’ signal.  However, if object value changes during
        C{callback} execution, C{with_changes_frozen} method will emit ‘changed’ signal
        once, after C{callback} returns.

        Calls to this method can be nested, i.e. C{callback} can call
        C{with_changes_frozen} on the same object too.  In this case, any nested calls
        will I{not} emit ‘changed’ signal, leaving it for the outmost call.

        This method is useful in the following cases:

          - you expect many changes in object’s value, but want interested parties be
            informed about final result only, not about all intermediate states;

          - you expect at least two changes and the final result may be “no changes”
            compared to original;

          - you expect many changes, don’t care about intermediate states and want to
            improve performance.

        In the second case, if the result is indeed “no changes”, this method ensures that
        ‘changed’ signal is not emitted at all.

        @note:
        There exists C{L{changes_frozen}} method with the same semantics.  It is only
        available on Python 2.5 and later, but allows to use the C{with} language
        statement and is preferred, if available.  This method is provided only since
        Py-notify supports Python versions starting with 2.3.

        @rtype:   C{object}
        @returns: Whatever C{callback} returns, unchanged. 
        """

        # Note: keep in sync with changes_frozen() in `notify/_2_5/base.py'.

        if self.__flags >= 0:
            original_value  = self.get ()
            self.__flags   -= 4

            try:
                return callback (*arguments, **keywords)
            finally:
                self.__flags += 4
                new_value     = self.get ()

                if new_value != original_value:
                    self._value_changed (new_value)
        else:
            return callback (*arguments, **keywords)


    changed = property (__get_changed_signal,
                        doc = ("""
                        The ‘changed’ signal for this object.  ‘Changed’ signal is emitted
                        if and only if the current value is changed and the object is not
                        L{frozen <is_frozen>}.  User of the object must never emit the
                        signal herself, but may operate with its handlers.
                        
                        Internally, reading this property creates the signal if it hasn’t
                        been created yet.  Derived classes may assume this behaviour.

                        @type: C{L{AbstractSignal}}
                        """))



    def _additional_description (self, formatter):
        """
        Generate list of additional descriptions for this object.  All description strings
        are put in parentheses after basic object description and are separated by
        semicolons.  Default description mentions number of handlers of ‘changed’ signal,
        if there are any at all.

        C{formatter} is either C{repr} or C{str} and should be used to format objects
        mentioned in list string(s).  Its use is not required but encouraged.

        Overriden method should look like this:

            >>> def _additional_description (self, formatter):
            ...     return (['my-description']
            ...             + super (..., self)._additional_description (formatter))

        You may selectively remove descriptions generated by superclasses, but remember
        that some of them (including this class) may generate varying number of
        descriptions, so this may be not trivial to do.  In general, there are no
        requirements on contents of returned list, except that it must contain only
        strings.

        This method is called by standard implementations of C{L{__repr__}} and
        C{L{__str__}}.  If you use your own (and that is perfectly fine), you don’t need
        to override this method.

        @param formatter: function (either C{repr} or C{str}) that can be used to format
                          various objects.

        @rtype:           C{list}
        @returns:         List of description strings for this object.
        """

        if self._has_signal ():
            num_handlers = self.__get_changed_signal ().count_handlers ()

            if num_handlers > 1:
                return ['%d handlers' % num_handlers]
            elif num_handlers == 1:
                return ['1 handler']

        return []

    def __to_string (self, strict):
        if strict:
            additional_description = self._additional_description (repr)
        else:
            additional_description = self._additional_description (str)

        if additional_description:
            return ' (%s)' % '; '.join (additional_description)
        else:
            return ''


    def __repr__(self):
        # It is impossible to recreate signal, so don't try to generate a valid Python
        # expression.
        return '<%s.%s: %s%s>' % (self.__module__, self.__class__.__name__,
                                  repr (self.get ()), self.__to_string (True))


    def __str__(self):
        return '<%s: %s%s>' % (self.__class__.__name__,
                               str (self.get ()), self.__to_string (False))


    def derive_type (cls, new_class_name, **options):
        """
        Derive and return a new type named C{new_class_name}.  Various C{options} define
        behaviour of instances of the new type.  Their set and sometimes semantics are
        defined by exact class this method is called for.

        @param new_class_name: name of the new class—important mostly for C{__str__} and
                               C{__repr__} implementations.
        @type  new_class_name: C{basestring}

        @param options:        options for the new type, as listed below.

        @newfield option:      Option, Options

        @option:               C{object} — valid Python identifier.  If specified, derived
                               type’s constructor will accept one parameter and store it
                               inside the created instance.  It will be used for calling
                               C{getter} and C{setter} functions.

        @option:               C{property} — valid Python identifier.  If specified,
                               C{object}’s value will be readable through a property, but
                               not writable.

        @option:               C{dict} — if true, derived type will have a C{__dict__}
                               slot, allowing setting any attribute on it.  This is
                               silently ignored if this class objects already have a dict.

        @option:               C{getter} — a callable accepting one argument, whose return
                               value will be used as C{L{get}} method result.  If
                               C{object} option is specified, the only argument will be
                               the one passed to instance constructor, else it will be
                               C{self} as passed to C{get} method.

        @option:               C{setter} — a callable accepting two argument, which will
                               be called from C{L{set}} method.  The first argument is
                               described in C{getter} option; the second is the C{value}
                               as passed to C{L{set}} method.

        @rtype:                C{type}

        @raises TypeError:     if C{new_class_name} is not a string or is not a valid
                               Python identifier.
        @raises exception:     whatever C{L{_generate_derived_type_dictionary}} raises, if
                               anything.
        """

        if not is_valid_identifier (new_class_name):
            raise TypeError ("'%s' is not a valid Python identifier" % new_class_name)

        full_options                   = dict (options)
        full_options['cls']            = cls
        full_options['new_class_name'] = new_class_name

        dictionary = { '__slots__': () }

        for value in cls._generate_derived_type_dictionary (full_options):
            if value[0] != '__slots__':
                dictionary[value[0]] = value[1]
            else:
                if isinstance (value[1], StringType):
                    dictionary['__slots__'] += (value[1],)
                else:
                    dictionary['__slots__'] += tuple (value[1])

        metaclass = dictionary.get ('__metaclass__', type (cls))
        new_type  = metaclass (new_class_name, (cls,), dictionary)

        try:
            raise Exception
        except Exception:
            try:
                # We try to pretend that the new type is created by the caller module, not
                # by `notify.base'.  That will give more helpful __repr__ result.
                traceback           = sys.exc_info () [2]
                new_type.__module__ = traceback.tb_frame.f_back.f_globals['__name__']
            except RuntimeError:
                # We can do nothing, ignore.
                pass

        return new_type


    def _generate_derived_type_dictionary (cls, options):
        """
        Generate an iterable of pairs in the form (Python identifier, value) for a new
        type created by C{L{derive_type}}.  Exact pairs should be influenced by
        C{options}, which are C{options} as passed to C{derive_type} plus C{cls} (for
        convenience) and C{new_class_name}.

        This method is not meant to be callable from outside, use C{L{derive_type}} for
        that instead.

        Overriden implementations of this method are recommended but not required to be
        generator functions.  They should generally start like this:

            >>> def _generate_derived_type_dictionary (cls, options):
            ...     for attribute in super (..., cls)._generate_derived_type_dictionary (options):
            ...         yield attribute
            ...
            ...     ...

        That is only an approximation and you can, for instance, change or override
        attributes returned by super-method.

        C{options} dictionary is constructed in such a way you should be able to evaluate
        all function-defining statements in it.  For instance, you can write own
        C{_generate_derived_type_dictionary} like this:

            >>> def _generate_derived_type_dictionary (cls, options):
            ...     ...
            ...
            ...     functions = {}
            ...
            ...     if 'foo_value' in options:
            ...         exec 'def foo (self): return foo_value' \
            ...              in { 'foo_value': options['foo_value'] }, functions
            ...
            ...     ...
            ...
            ...     for function in functions.iteritems ():
            ...         yield function

        Returned value for C{__slots__} is treated specially.  While normally values
        associated with the same name override previous values, values for C{__slots__}
        are combined into a tuple instead.

        Note that it is not recommended to use C{options} for execution globals or locals
        dictionary directly.  This way your code may become vulnerable to other option
        addition, e.g. for some derivative of the class.  For instance, you may use
        C{property} built-in, then setting it in C{options} will hide the built-in from
        your code.  Consider using C{L{_filter_options}} utility method.

        @param options:    dictionary of options passed to C{L{derive_type}} method, plus
                           C{cls} and C{new_class_name}.
        @type  options:    C{dict}

        @rtype:            iterable
        @returns:          Pairs of (Python identifier, value) for the new type.

        @raises exception: if there is any error in C{options}.
        """

        functions        = {}
        filtered_options = AbstractValueObject._filter_options (options, 'cls', 'getter', 'setter')


        if 'object' in options:
            object = options['object']
            if not is_valid_identifier (object):
                raise ValueError ("'%s' is not a valid Python identifier" % object)

            yield '__slots__', mangle_identifier (options['new_class_name'], object)

            execute (('def __init__(self, %s):\n'
                      '    cls.__init__(self)\n'
                      '    %s = %s')
                     % (object, AbstractValueObject._get_object (options), object),
                     filtered_options, functions)

            if 'property' in options:
                property = options['property']
                if property == object:
                    raise ValueError ("'property' option cannot be the same as 'object'")

                if not is_valid_identifier (property):
                    raise ValueError ("'%s' is not a valid Python identifier" % property)

                execute ('%s = property (lambda self: %s)'
                         % (mangle_identifier (options['new_class_name'], property),
                            AbstractValueObject._get_object (options)),
                         functions)

        else:
            if 'property' in options:
                raise ValueError ("'property' without 'object' option doesn't make sense")

        if 'dict' in options and options['dict']:
            # Gracefully ignore if this type already has a dict.
            if not cls.__dictoffset__:
                yield '__slots__', '__dict__'

        if 'getter' in options:
            if not is_callable (options['getter']):
                raise TypeError ("'getter' must be a callable")

            execute ('def get (self): return getter (%s)'
                     % AbstractValueObject._get_object (options),
                     filtered_options, functions)

        if 'setter' in options:
            if not is_callable (options['setter']):
                raise TypeError ("'setter' must be a callable")

            execute ('def set (self, value): return setter (%s, value)'
                     % AbstractValueObject._get_object (options),
                     filtered_options, functions)

        for function in functions.items ():
            yield function


    def _get_object (options):
        """
        Return Python expression for object that should be passed to various user
        functions.  This is either C{"self"} or C{"self.some_attribute"} if C{options}
        dictionary contains C{"object"} key.  In this case C{"some_attribute"} string is
        evaluated to a private attribute name for the class being defined.

        This is a helper for C{L{_generate_derived_type_dictionary}} only.  It should not
        be called from outside.

        @param options: the same value as passed to C{_generate_derived_type_dictionary}.
        @type  options: C{dict}

        @rtype:         C{str}
        """

        if 'object' in options:
            return 'self.%s' % mangle_identifier (options['new_class_name'], options['object'])
        else:
            return 'self'


    def _filter_options (options, *names):
        """
        Return a subset of C{options} including only those listed in C{names}.  This is a
        utility method.  Its main purpose is to build a subset of options dictionary for
        C{L{_generate_derived_type_dictionary}} method, which is safe to use as locals or
        globals for evaluating method definitions.

        @param options: full dictionary of options.
        @type  options: C{dict}

        @param names:   permitted options.

        @rtype:         C{dict}
        """

        filtered_options = {}

        for name in names:
            if name in options:
                filtered_options[name] = options[name]

        return filtered_options


    derive_type                       = classmethod  (derive_type)
    _generate_derived_type_dictionary = classmethod  (_generate_derived_type_dictionary)
    _get_object                       = staticmethod (_get_object)
    _filter_options                   = staticmethod (_filter_options)



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
