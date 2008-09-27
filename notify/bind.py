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
Bindings are callables with advanced comparing capabilities.  This can be useful when
equality/inequality test is required as is the case with L{signals <signal>}.  For
instance, the main difference from lambdas can be shown with this example:

    >>> a = lambda x: x + 3
    ... b = lambda x: x + 3
    ... a != b
    ...
    ... import operator
    ... from notify.bind import *
    ...
    ... p = Binding (operator.add, 3)
    ... q = Binding (operator.add, 3)
    ... p == q
    ...
    ... a (10) == p (10)  # Check that it indeed does what it should.

So, lambdas are great and provide more functionality than bindings, but they won’t work if
you need comparing callables for equality.

Another thing not possible with lambdas (or bound methods, for that matter) is to bind
object I{weakly}.  In other words, as long as there is a bound method or lambda in
existence, object is considered referenced and won’t be garbage-collected.  This can be
good, but not always what you want.

Class C{L{WeakBinding}} and its descendants bind object weakly.  In other words, as long
as object is not garbage-collected, e.g. referenced from somewhere, they work just like
normal C{L{Binding}}.  However, they don’t create a strong reference to the object and, if
it is destroyed, things get different: C{WeakBinding} does nothing when called, while
C{L{RaisingWeakBinding}} raises C{L{GarbageCollectedError}} exception.

Finally, it is possible to create bindings with a list of precreated arguments.  Any
arguments passed to binding’s C{L{__call__ <Binding.__call__>}} method will be I{appended}
to this list and passed to the wrapped callable together.  Of course, this and more is
possible with lambdas and is not an advantage of bindings, just a feature.
"""

__docformat__ = 'epytext en'
__all__       = ('Binding', 'WeakBinding', 'RaisingWeakBinding',
                 'BindingCompatibleTypes',
                 'CannotWeakReferenceError', 'GarbageCollectedError')


import sys
from types        import FunctionType, MethodType
import weakref

from notify.utils import is_callable, frozendict, DummyReference



_PY3K = (sys.version_info[0] >= 3)



#-- Base binding class -----------------------------------------------

# Note on (not) using `functools.partial' in Python 2.5 and up.  I have investigated the
# possibility, but it doesn't seem useful.  It gave no visible speed up even on
# `emission.EmissionBenchmark1' (which uses functional handlers.)  Besides, using
# `partial' would complicate the code, because it would bind the object strongly (hence
# unusable for `WeakBinding' below), won't compare as needed by itself and so on.
#
# Conclusion: let's not use it at all.

class Binding (object):

    """
    Bindings are a kind of callables with advanced comparing capabilities.  More
    specifically, bindings can wrap any other callable, including functions and methods,
    adding optional arguments specified at creation time.  Bindings, wrapping equal
    callables and with equal argument lists, will be equal.
    """

    __slots__ = ('_object', '_function', '_class', '_arguments', '_keywords')


    def __init__(self, callable_object, arguments = (), keywords = None):
        """
        Initialize a new binding which will call C{callable_object}, I{prepending} fixed
        C{arguments} (if any) to those specified at call time.  Here, C{callable_object}
        is usually a function or a method, but can in principle be anything callable,
        including an already existing binding.

        See also C{L{wrap}} class method for a different way of creating bindings.

        @param  callable_object: the callable object that will be invoked by this binding
                                 from C{L{__call__}} method.
        @type   callable_object: callable

        @param  arguments:       optional list of argument for C{callable_object} that
                                 will be prepended to call arguments.
        @type   arguments:       iterable

        @raises TypeError:       if C{callable_object} is not callable or C{arguments} is
                                 not iterable.
        """

        if not is_callable (callable_object):
            raise TypeError ("'callable_object' must be callable")

        # This raises `TypeError' if `arguments' or `keywords' type is inappropriate.
        arguments = tuple (arguments)
        if keywords is None:
            keywords = frozendict.EMPTY
        # Note: not isinstance, subclasses might become modifiable again.
        elif type (keywords) is not frozendict:
            keywords = frozendict (keywords)

        super (Binding, self).__init__()

        if isinstance (callable_object, BindingCompatibleTypes):
            if _PY3K:
                self._object   = callable_object.__self__
                self._function = callable_object.__func__
                self._class    = type (self._object)
            else:
                self._object   = callable_object.im_self
                self._function = callable_object.im_func
                self._class    = callable_object.im_class
        else:
            self._object   = None
            self._function = callable_object
            self._class    = None

        self._arguments = arguments
        self._keywords  = keywords


    def wrap (cls, callable_object, arguments = (), keywords = None):
        """
        Return a callable with semantics of the binding class this method is called for.
        I{If necessary} (e.g. if C{arguments} tuple is not empty), this method creates a
        binding instance first.  In any case, you can assume that returned object will
        I{behave} identically to an instance of this class with C{callable_object} and
        C{arguments} passed to C{L{__init__}} method.  However, the returned object I{is
        not required} to be an instance.

        This is the preferred method of creating bindings.  It is generally more memory-
        and call-time-efficient since in some cases no new objects are created at all.

        @param  callable_object: the callable object that will be invoked by this binding
                                 from C{L{__call__}} method.
        @type   callable_object: callable

        @param  arguments:       optional list of argument for C{callable_object} that
                                 will be prepended to call arguments.
        @type   arguments:       iterable

        @rtype:            callable

        @raises TypeError: if C{callable_object} is not callable or C{arguments} is not
                           iterable.
        """

        if arguments or keywords:
            return cls (callable_object, arguments, keywords)
        else:
            if not is_callable (callable_object):
                raise TypeError ("'callable_object' must be callable")

            return callable_object


    wrap = classmethod (wrap)


    def _get_object (self):
        """
        Return object associated with this binding.  This is the internal getter method
        for C{L{im_self}} property and outside code should use the property, not this
        method directly.

        @note:  Never override C{im_self} property, override this method instead.

        @rtype: C{object}
        """

        return self._object

    def _get_function (self):
        """
        Return raw function associated with this binding.  This is the internal getter
        method for C{L{im_func}} property and outside code should use the property, not
        this method directly.

        @note:  Never override C{im_func} property, override this method instead.

        @rtype: function
        """

        return self._function

    def _get_class (self):
        """
        Return the class associated with this binding.  This is the internal getter method
        for C{L{im_class}} property and outside code should use the property, not this
        method directly.

        @note:  Never override C{im_class} property, override this method instead.

        @rtype: C{types.ClassType} or C{type}
        """

        return self._class

    def _get_arguments (self):
        """
        Get the arguments of this binding.  This is the internal getter method for
        C{L{im_args}} property and outside code should use the property, not this method
        directly.

        @note:  Never override C{im_args} property, override this method instead.

        @rtype: C{tuple}
        """

        return self._arguments

    def _get_keywords (self):
        return self._keywords


    def __call__(self, *arguments, **keywords):
        """
        Call the wrapped callable (e.g. method or function) and return whatever it
        returns.  If binding was constructed with L{arguments <im_args>}, they are
        I{prepended} to arguments of this function before being passed to the wrapped
        callable.

        @param  arguments: optional call arguments.

        @rtype:            C{object}

        @raises exception: whatever wrapped method raises, if anything.
        """

        # NOTE: If, for some reason, you change this, don't forget to adjust
        #       `WeakBinding.__call__' accordingly.
        if keywords:
            fixed_keywords = self._get_keywords ()
            if fixed_keywords:
                all_keywords = dict (fixed_keywords)
                all_keywords.update (keywords)
            else:
                all_keywords = keywords
        else:
            all_keywords = self._get_keywords ()

        if self._get_class () is not None:
            return self._get_function () (self._get_object (),
                                          *(self._get_arguments () + arguments),
                                          **all_keywords)
        else:
            return self._get_function () (*(self._get_arguments () + arguments),
                                          **all_keywords)


    def __eq__(self, other):
        """
        Determine if C{self} is equal to C{other}.  Two bindings are equal only if they
        wrap equal methods and have equal L{argument lists <im_args>}.  A binding with an
        empty argument list is also equal to its wrapped method or function.

        @rtype: C{bool}
        """

        if self is other:
            return True

        if isinstance (other, BindingCompatibleTypes):
            if _PY3K:
                if (self._get_object      () is not other.__self__
                    or self._get_function () is not other.__func__):
                    return False
            else:
                if (self._get_object      () is not other.im_self
                    or self._get_function () is not other.im_func
                    or self._get_class    () is not other.im_class):
                    return False

            if isinstance (other, Binding):
                return (self    ._get_arguments () == other._get_arguments ()
                        and self._get_keywords  () == other._get_keywords  ())
            else:
                return not self._get_arguments () and not self._get_keywords ()

        elif isinstance (other, FunctionType):
            return (self    ._get_function () is other
                    and self._get_object   () is None
                    and self._get_class    () is None
                    and not self._get_arguments ()
                    and not self._get_keywords  ())

        else:
            return NotImplemented


    def __ne__(self, other):
        """
        Determine if C{self} is not equal to C{other}.  See C{L{__eq__}} for details.

        @rtype: C{bool}
        """

        equal = self.__eq__(other)

        if equal is not NotImplemented:
            return not equal
        else:
            return NotImplemented


    def __hash__(self):
        _class    = self._get_class     ()
        object    = self._get_object    ()
        arguments = self._get_arguments ()
        keywords  = self._get_keywords  ()

        if _class is not None or object is not None:
            _hash = hash (MethodType (self._get_function (), object, _class))
        else:
            _hash = hash (self._get_function ())

        if arguments:
            _hash ^= hash (arguments)
        if keywords:
            _hash ^= hash (keywords)

        return _hash


    def __nonzero__(self):
        """
        C{True} if binding is in its initial and fully functional state.  This method
        mainly exists for L{weak bindings <WeakBinding>}, for which it returns C{False}
        if binding’s object has been garbage-collected.

        @rtype:   C{bool}
        @returns: Always C{True} for this class.
        """

        return True

    if _PY3K:
        __bool__ = __nonzero__
        del __nonzero__


    im_self  = property (lambda self: self._get_object (),
                         doc = ("""
                                The object of this binding or C{None} if it has been
                                garbage-collected already.  The name of the property is
                                kept identical to a similar property of method objects,
                                therefore it is nonstandard.

                                @type: object

                                @note: Never override this property, override
                                       C{L{_get_object}} method instead.
                                """))
    im_func  = property (lambda self: self._get_function (),
                         doc = ("""
                                Function of this binding.  The name of the property is
                                kept identical to a similar property of method objects,
                                therefore it is nonstandard.

                                @type: function

                                @note: Never override this property, override
                                       C{L{_get_function}} method instead.
                                """))
    im_class = property (lambda self: self._get_class (),
                         doc = ("""
                                Class of this binding’s object.  The name of the property
                                is kept identical to a similar property of method objects,
                                therefore it is nonstandard.

                                @type: class or type

                                @note: Never override this property, override
                                       C{L{_get_class}} method instead.
                                """))
    im_args  = property (lambda self: self._get_arguments (),
                         doc = ("""
                                Arguments of this binding as passed to C{L{__init__}} or
                                C{L{wrap}} method.  When calling the binding, they are
                                I{prepended} to arguments passed to C{L{__call__}}.  The
                                name of the property is kept uniform with with
                                C{L{im_self}} and friends, therefore it is nonstandard.

                                @type: tuple

                                @note: Never override this property, override
                                       C{L{_get_arguments}} method instead.
                                """))

    im_kwds  = property (lambda self: self._get_keywords ())


    if _PY3K:
        __self__ = im_self
        __func__ = im_func
        __cls__  = im_class
        __args__ = im_args
        __kwds__ = im_kwds

        del im_self
        del im_func
        del im_class
        del im_args
        del im_kwds


    def __repr__(self):
        return self.__to_string ('%s.%s' % (self.__module__, self.__class__.__name__), True)

    def __str__(self):
        return self.__to_string (self.__class__.__name__, False)

    def __to_string (self, class_name, strict):
        if strict:
            formatter = repr
        else:
            formatter = str

        _class    = self._get_class     ()
        function  = self._get_function  ()
        arguments = self._get_arguments ()
        keywords  = self._get_keywords  ()

        if isinstance (function, FunctionType):
            function_description = function.__name__
        else:
            function_description = formatter (function)

        description = '%s at 0x%x' % (class_name, id (self))

        if _class is not None:
            object = self._get_object ()

            if object is not None:
                description = ('bound %s for %s.%s of %s'
                               % (description, _class.__name__, function_description,
                                  formatter (object)))
            else:
                description = ('unbound %s for %s.%s'
                               % (description, _class.__name__, function_description))
        else:
            description = '%s for %s' % (description, function_description)

        if arguments:
            if keywords:
                return ('<%s (%s, ...., **{%s, ...})>'
                        % (description,
                           ', '.join ([formatter (argument) for argument in arguments]),
                           ', '.join (['%s=%s' % (formatter (key), formatter (value))
                                       for key, value in keywords.items ()])))
            else:
                return ('<%s (%s, ...)>'
                        % (description,
                           ', '.join ([formatter (argument) for argument in arguments])))
        else:
            if keywords:
                return ('<%s (**{%s, ...})>'
                        % (description,
                           ', '.join (['%s=%s' % (formatter (key), formatter (value))
                                       for key, value in keywords.items ()])))
            else:
                return '<%s>' % description


BindingCompatibleTypes = (MethodType, Binding)
"""
Types ‘compatible’ with C{L{Binding}} to certain extent.  These include
C{types.MethodType} and C{Binding} itself.  Both have C{im_self}, C{im_class} and
C{im_func} properties (though C{im_args} is unique to C{Binding}.)  Rationale to have this
variable is similar to that of C{weakref.ProxyTypes}.  In particular, implementation
itself uses the variable several times in calls to C{isinstance} function.
"""



#-- Weak binding classes ---------------------------------------------

# Implementation note: self._object can contain a real WeakReference, a _NONE_REFERENCE or
# None.  _NONE_REFERENCE is stored if the binding is created without an object at all
# (i.e. not for a method, or for a static method.)  None indicates that the binding was
# created with an object, but it has been garbage-collected.

class WeakBinding (Binding):

    """
    A kind of L{binding <Binding>} which refers to its object weakly.  In other words,
    existence of such a binding doesn’t prevent its object from being garbage-collected if
    it is not strongly referenced somewhere else.

    As long as object is not garbage-collected, such a binding behaves identically to an
    instance of its superclass.  However, once object I{is} garbage-collected, things
    change:

        - C{L{__call__}} does nothing and returns C{None};

        - C{L{im_self}} becomes C{None};

        - boolean state (see C{L{__nonzero__}} method) of the binding becomes C{False}.

    @see:  RaisingWeakBinding
    """

    __slots__ = ('__callback', '__hash')


    def __init__(self, callable_object, arguments = (), callback = None, keywords = None):
        """
        Initialize a new weak binding which will call C{callable_object}, I{prepending}
        fixed C{arguments} (if any) to those specified at call time.  Here,
        C{callable_object} is usually a function or a method, but can in principle be
        anything callable, including an already existing binding.

        If C{callable_object} is a bound method, its object is referenced weakly.  It is
        also legal to create weak bindings for other callables, but they will behave
        identically to plain bindings in that case.

        See also C{L{wrap}} class method for a different way of creating weak bindings.

        @param  callable_object: the callable object that will be invoked by this binding
                                 from C{L{__call__}} method.
        @type   callable_object: callable

        @param  arguments:       optional list of argument for C{callable_object} that
                                 will be prepended to call arguments.
        @type   arguments:       iterable

        @param  callback:        optional callable that will be called if binding’s object
                                 is garbage-collected.
        @type   callback:        callable or C{None}

        @raises TypeError:                if C{callable_object} is not callable or
                                          C{arguments} is not iterable.
        @raises CannotWeakReferenceError: if C{callable_object} is a bound method, but
                                          its object is not weakly referencable.
        """

        super (WeakBinding, self).__init__(callable_object, arguments, keywords)

        if self._object is not None:
            if callback is not None and not is_callable (callback):
                raise TypeError ("'callback' must be callable")

            try:
                self.__callback = callback
                self._object    = weakref.ref (self._object, self.__object_garbage_collected)
            except:
                raise CannotWeakReferenceError (self._object)
        else:
            self._object = _NONE_REFERENCE

        self.__hash = None


    def wrap (cls, callable_object, arguments = (), callback = None, keywords = None):
        # Inherit documentation somehow?
        if arguments or keywords:
            return cls (callable_object, arguments, callback, keywords)

        if (isinstance (callable_object, BindingCompatibleTypes)
            and not isinstance (callable_object, WeakBinding)):

            if _PY3K:
                if callable_object.__self__ is not None:
                    return cls (callable_object, arguments, callback, keywords)
            else:
                if callable_object.im_self is not None:
                    return cls (callable_object, arguments, callback, keywords)

        return callable_object


    wrap = classmethod (wrap)


    def _get_object (self):
        reference = self._object

        if reference is not None:
            return reference ()
        else:
            return None


    def __call__(self, *arguments, **keywords):
        """
        Like C{L{Binding.__call__}}, but account for garbage-collected objects.  If object
        has been garbage-collected, then do nothing and return C{None}.

        @param  arguments: optional call arguments.

        @rtype:            C{object}

        @raises exception: whatever wrapped method raises, if anything.
        """

        reference = self._object

        if reference is not None:
            # FIXME: Resurrect 0.2 optimization of inlining super method once that is more
            #        stable.  It is an _important_ optimization.
            return super (WeakBinding, self).__call__(*arguments, **keywords)
        else:
            return self._call_after_garbage_collecting ()


    def _call_after_garbage_collecting (self):
        """
        Method called if the binding is called after its object has been
        garbage-collected.  Default implementation just returns C{None}.  Note that the
        return value is then returned from C{L{__call__}}.

        Please note that the condition for calling above is precise.  In particular, if
        the binding was created without an object (i.e. with C{None}) to begin with, this
        method will never be called at all.

        @rtype: C{object}
        """

        return None


    def __object_garbage_collected (self, reference):
        self._object = None

        callback = self.__callback
        if callback is not None:
            self.__callback = None
            callback (reference)


    def __hash__(self):
        if self.__hash is None:
            if self:
                self.__hash = super (WeakBinding, self).__hash__()
            else:
                raise TypeError (("%s's object had been garbage-collected "
                                  "before first call to __hash__()")
                                 % self.__class__.__name__)

        return self.__hash


    def __nonzero__(self):
        """
        C{True} if method’s object hasn’t been garbage-collected.  More precisely, C{True}
        if binding is in its initial and fully functional state, but for weak bindings it
        means exactly what is stated in the previous statement.

        @rtype: C{bool}
        """

        return self._object is not None

    if _PY3K:
        __bool__ = __nonzero__
        del __nonzero__


_NONE_REFERENCE = DummyReference (None)



class RaisingWeakBinding (WeakBinding):

    """
    A variation of L{weak binding <WeakBinding>} which raises C{L{GarbageCollectedError}}
    if called after its object has been garbage-collected.  There are no other difference
    from common weak bindings.  In particular, if a binding is created without an object
    (i.e. with C{None}) to begin with, it will never raise C{L{GarbageCollectedError}}.
    """

    __slots__    = ()


    def _call_after_garbage_collecting (self):
        raise GarbageCollectedError



#-- Exception types for weak bindings --------------------------------

class CannotWeakReferenceError (TypeError):

    """
    Exception thrown when trying to create a L{weak binding <WeakBinding>} for an object
    that doesn’t support weak references.
    """

    pass



class GarbageCollectedError (RuntimeError):

    """
    Exception thrown when calling an instance of C{L{RaisingWeakBinding}} with a
    garbage-collected object.
    """

    pass



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
