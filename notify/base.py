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
Mostly internal module that contains functionality common to L{conditions <condition>} and
L{variables <variable>}.  You can use C{L{AbstractValueObject}} class directly, if really
needed, but almost always conditions or variables is what you need.
"""

__docformat__ = 'epytext en'
__all__       = ('AbstractValueObject',)


import types

from notify.mediator import *
from notify.signal   import *
from notify.utils    import *



#-- Base class for conditions and variables --------------------------

class AbstractValueObject (object):

    """
    Base class for C{L{AbstractCondition <condition.AbstractCondition>}} and
    C{L{AbstractVariable <variable.AbstractVariable>}} implementing common functionality.
    """

    __slots__ = ('_AbstractValueObject__signal', '__weakref__')


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


    def get (self):
        """
        Get the current value of the object.  Note that the default implementation just
        raises C{NotImplementedError}, since the current value is not stored by default.

        @rtype: object
        """

        raise_not_implemented_exception (self)

    def set (self, value):
        """
        Set the current value to C{value}, if possible.  Default implementation always
        raises C{NotImplementedError} as it is not mutable.

        @raises NotImplementedError: if the object is not mutable.
        @raises ValueError:          if C{value} is not suitable for some reason.

        @rtype:                      bool
        @returns:                    Whether setting value had any effect, i.e. C{True}
                                     if C{value} is not equal to result of C{L{get}}
                                     method.
        """

        raise_not_implemented_exception (self)


    def _is_mutable (self):
        """
        Determine if object is mutable and thus if C{L{set}} method can be called at all.
        Default implementation assumes that if derived class overrides C{set} method, its
        instances are mutable.  This method should be overriden if that’s not the case.

        This method may be used from outside, but you should consider using C{L{mutable}}
        property instead, as it is public and more convenient.

        @rtype: bool
        """

        return self.set.im_func is not AbstractValueObject.set.im_func


    mutable = property (lambda self: self._is_mutable (),
                        doc = ("""
                               Read-only property indicating if this object is mutable.
                               In other words, if object’s value can be changed by
                               C{L{set}} method, or if it is computed by some means and
                               not settable from outside.

                               @type: bool
                               """))


    def __get_changed_signal (self):
        if self.__signal is not None:
            signal = self.__signal
            if not isinstance (signal, AbstractSignal):
                signal = signal ()
        else:
            signal, self.__signal = self._create_signal ()

        return signal


    def _create_signal (self):
        """
        Create the signal that will be returned by C{L{changed}} property.  Default
        implementation returns an instance of C{L{Signal <signal.Signal>}} class without
        accumulator, but derived classes may wish to override this.

        Note that this method will be called only when getting C{changed} property and
        only if there is no signal yet.  I.e. only for the first invocation at all or
        first invocation after a call to C{L{_remove_signal}}.

        @rtype:   AbstractSignal, object
        @returns: A signal object I{or} a reference to one (i.e. object with C{__call__}
                  method returning a signal.)
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

        @rtype: bool
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

        @rtype:   bool
        @returns: Whether ‘changed’ signal is removed.
        """

        if self.__signal is signal:
            self.__signal = None
            return True
        else:
            return False


    def store (self, handler, *arguments):
        """
        Make sure current value is ‘transmitted’ to C{handler} (with C{arguments}).  This
        means that the C{handler} is called once with the C{arguments} and the current
        value and afterwards each time the current value changes.  The only argument
        passed to C{handler} in addition to specified ones is the value as returned by the
        C{L{get}} method.

        See C{L{AbstractSignal.connect}} method description for details how C{arguments}
        are handled.

        @raises TypeError: if C{handler} is not callable or cannot be called with
                           C{arguments} and current object value.
        """

        handler (*(arguments + (self.get (),)))
        self.__get_changed_signal ().connect (handler, *arguments)

    def store_safe (self, handler, *arguments):
        """
        Like C{L{store}}, except that if C{handler} is already connected to this object’s
        ‘changed’ signal, this method does nothing.  See C{L{Signal.connect_safe}} method
        for details.

        @raises TypeError: if C{handler} is not callable or cannot be called with
                           C{arguments} and current object value.
        @rtype:            bool
        @returns:          Whether C{handler} is connected to ‘changed’ signal.
        """

        if not self.__get_changed_signal ().is_connected (handler, *arguments):
            handler (*(arguments + (self.get (),)))
            self.__get_changed_signal ().connect (handler, *arguments)

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

        @raises TypeError:  if C{value_object} is not an C{AbstractValueObject} or
                            C{mediator} is neither C{None} nor an instance of
                            C{L{AbstractMediator <mediator.AbstractMediator>}}.
        @raises ValueError: if either C{self} or C{value_object} is not mutable.
        @raises ValueError: if current value of C{value_object} is not suitable for
                            C{self}.
        """

        if not isinstance (value_object, AbstractValueObject):
            raise TypeError ("can only synchronize with other `AbstractValueObject' instances")

        if not self._is_mutable ():
            raise ValueError ("`%s' is not mutable" % self)

        if not value_object._is_mutable ():
            raise ValueError ("`%s' is not mutable" % value_object)

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
        Like C{L{synchronize}} except that uses L{store_safe} instead of L{store}.  See
        C{L{synchronize}} for details.

        @raises TypeError:  if C{value_object} is not an C{AbstractValueObject} or
                            C{mediator} is neither C{None} nor an instance of
                            C{L{AbstractMediator <mediator.AbstractMediator>}}.
        @raises ValueError: if either C{self} or C{value_object} is not mutable.
        @raises ValueError: if current value of C{value_object} is not suitable for
                            C{self}.
        """

        if not isinstance (value_object, AbstractValueObject):
            raise TypeError ("can only synchronize with other `AbstractValueObject' instances")

        if not value_object._is_mutable ():
            raise ValueError ("target `AbstractValueObject' instance is not mutable")

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

        @raises TypeError: if C{mediator} is neither C{None} nor an instance of
                           C{L{AbstractMediator <mediator.AbstractMediator>}}.

        @rtype:            bool
        @returns:          Whether C{self} and C{value_object} have been synchronized
                           before (using C{mediator} if it is not C{None}.)

        @note:
        If C{L{set}} method of one of the values has been connected to other value’s
        ‘changed’ signal, but otherwise is not true, this method does nothing and returns
        C{False}.  So, it should be safe unless C{L{synchronize}} has been called or its
        effect has been emulated manually.
        """

        if not isinstance (mediator, (types.NoneType, AbstractMediator)):
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

        @raises TypeError: if C{mediator} is neither C{None} nor an instance of
                           C{L{AbstractMediator <mediator.AbstractMediator>}}.

        @rtype:            bool
        @returns:          Whether C{self} and C{value_object} have been synchronized
                           before (using C{mediator} if it is not C{None}.)

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

        if not isinstance (mediator, (types.NoneType, AbstractMediator)):
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


    def _value_changed (self, new_value):
        """
        Method that must be called every time object’s value changes.  Note that this
        method I{must not} be called from outside, it is for class descendants only.

        To follow general contract of the class, this method must be called only when the
        value indeed changes, i.e when C{new_value} is not equal to C{self.get()}.
        C{_value_changed} itself does not check it and so this check (if needed) is up to
        implementing descendant class.

        For convenience, this method always returns C{True}.

        @rtype:   bool
        @returns: Always C{True}.
        """

        if self.__signal is not None:
            if isinstance (self.__signal, AbstractSignal):
                self.__signal (new_value)
            else:
                self.__signal () (new_value)

        return True


    changed = property (__get_changed_signal,
                        doc = ("""
                        The ‘changed’ signal for this object.  ‘Changed’ signal is emitted
                        if and only if the current value is changed.  User of the object
                        must never emit the signal herself, but may operate with its
                        handlers.
                        
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

        @rtype:   list
        @returns: List of description strings for this object.
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
        # It is impossible to recreate signal, so don't try to generate a valid Python
        # expression.
        return '<%s: %s%s>' % (self.__class__.__name__,
                               str (self.get ()), self.__to_string (False))


    def derive_type (self_class, new_class_name, **options):
        """
        Derive and return a new type named C{new_class_name}.  Various C{options} define
        behaviour of instances of the new type.  Their set and sometimes semantics are
        defined by exact class this method is called for.

        @newfield option:  Option, Options

        @option:           C{object} — valid Python identifier.  If specified, derived
                           type’s constructor will accept one parameter and store it
                           inside the created instance.  It will be used for calling
                           C{getter} and C{setter} functions.

        @option:           C{getter} — a callable accepting one argument, whose return
                           value will be used as C{L{get}} method result.  If C{object}
                           option is specified, the only argument will be the one passed
                           to instance constructor, else it will be C{self} as passed to
                           C{get} method.

        @option:           C{setter} — a callable accepting two argument, which will be
                           called from C{L{get}} method.  The first argument is described
                           in C{getter} option; the second is the C{value} as passed to
                           C{L{set}} method.

        @rtype:            type

        @raises TypeError: if C{new_class_name} is not a string or is not a valid Python
                           identifier.
        @raises exception: whatever C{L{_generate_derived_type_dictionary}} raises, if
                           anything.
        """

        if not is_valid_identifier (new_class_name):
            raise TypeError ("`%s' is not a valid Python identifier" % new_class_name)

        full_options = dict (options)
        full_options['self_class']     = self_class
        full_options['new_class_name'] = new_class_name

        dictionary = {}

        for value in self_class._generate_derived_type_dictionary (full_options):
            if value[0] != '__slots__':
                dictionary[value[0]] = value[1]
            else:
                if not '__slots__' in dictionary:
                    dictionary['__slots__'] = ()

                dictionary['__slots__'] += tuple (value[1])

        try:
            # FIXME: I'm not sure this is not a hack.
            return type (new_class_name, (self_class,), dictionary)
        finally:
            del dictionary


    def _generate_derived_type_dictionary (self_class, options):
        """
        Generate an iterable of pairs in the form (Python identifier, value) for a new
        type created by C{L{derive_type}}.  Exact pairs should be influenced by
        C{options}, which are C{options} as passed to C{derive_type} plus C{self_class}
        (for convenience) and C{new_class_name}.

        This method is not meant to be callable from outside, use C{L{derive_type}} for
        that instead.

        Overriden implementations of this method are recommended but not required to be
        generator functions.  They should generally start like this:

            >>> def _generate_derived_type_dictionary (self_class, options):
            ...     for attribute in super (..., self_class)._generate_derived_type_dictionary (options):
            ...         yield attribute
            ...
            ...     ...

        That is only an approximation and you can, for instance, change or override
        attributes returned by super-method.

        C{options} dictionary is constructed in such a way you should be able to evaluate
        all function-defining statements in it.  For instance, you can write own
        C{_generate_derived_type_dictionary} like this:

            >>> def _generate_derived_type_dictionary (self_class, options):
            ...     ...
            ...
            ...     functions = {}
            ...
            ...     if 'foo_value' in options:
            ...         exec 'def foo (self): return foo_value' in options, functions
            ...
            ...     ...
            ...
            ...     for function in functions.iteritems ():
            ...         yield function

        Returned value for C{__slots__} is treated specially.  While normally values
        associated with the same name override previous values, values for C{__slots__}
        are combined in to a tuple instead.

        @rtype:            iterable
        @returns:          Pairs of (Python identifier, value) for the new type.
        @raises exception: if there is any error in C{options}.
        """

        functions = {}

        if 'object' in options:
            object = options['object']
            if not is_valid_identifier (object):
                raise ValueError ("`%s' is not a valid Python identifier" % object)

            yield '__slots__', ('_%s__%s' % (options['new_class_name'].lstrip ('_'), object),)

            exec (('def __init__(self, %s):\n'
                   '    self_class.__init__(self)\n'
                   '    %s = %s')
                  % (object, AbstractValueObject._get_object (options), object)) \
                  in options, functions

            del object

        if 'getter' in options:
            getter = options['getter']
            if not callable (getter):
                raise TypeError ("`getter' must be a callable")

            exec ('def get (self): return getter (%s)'
                  % AbstractValueObject._get_object (options))  in options, functions

        if 'setter' in options:
            setter = options['setter']
            if not callable (setter):
                raise TypeError ("`setter' must be a callable")

            exec ('def set (self, value): return setter (%s, value)'
                  % AbstractValueObject._get_object (options)) in options, functions

        for function in functions.iteritems ():
            yield function

        del functions


    def _get_object (options):
        """
        Return Python expression for object that should be passed to various user
        functions.  This is either C{"self"} or C{"self.some_attribute"} if C{options}
        dictionary contains C{"object"} key.  In this case C{"some_attribute"} string is
        evaluated to a private attribute name for the class being defined.

        This is a helper for C{_generate_derived_type_dictionary} only.  It should not be
        called from outside.

        @rtype: str
        """

        if 'object' in options:
            return 'self._%s__%s' % (options['new_class_name'].lstrip ('_'), options['object'])
        else:
            return 'self'


    derive_type                       = classmethod  (derive_type)
    _generate_derived_type_dictionary = classmethod  (_generate_derived_type_dictionary)
    _get_object                       = staticmethod (_get_object)



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
