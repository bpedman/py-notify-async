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

Class L{WeakBinding} and its descendants bind object weakly.  In other words, as long as
object is not garbage-collected, e.g. referenced from somewhere, they work just like
normal L{Binding}.  However, they don’t create a strong reference to the object and, if it
is destroyed, things get different: L{WeakBinding} does nothing when called, while
L{RaisingWeakBinding} raises L{GarbageCollectedError} exception.

Finally, it is possible to create bindings with a list of precreated arguments.  Any
arguments passed to binding’s L{__call__ <Binding.__call__>} method will be I{appended} to
this list and passed to wrapped callable together.  Of course, this and more is possible
with lambdas and is not an advantage of bindings, just a feature.
"""

__docformat__ = 'epytext en'
__all__       = ('Binding', 'WeakBinding', 'RaisingWeakBinding',
                 'BindingCompatibleTypes',
                 'CannotWeakReferenceError', 'GarbageCollectedError')


import types
import weakref

from notify.utils import *



#-- Base binding class -----------------------------------------------

class Binding (object):

    """
    Bindings are a kind of callables with advanced comparing capabilities.  More
    specifically, bindings can wrap any other callable, including functions and methods,
    adding optional arguments specified at creation time.  Bindings, wrapping equal
    callables and with equal argument lists, will be equal.
    """

    __slots__ = ('_object', '_function', '_class', '_arguments')


    def __init__(self, callable_object, arguments = ()):
        """
        Initialize a new binding which will call C{callable_object}, I{prepending} fixed
        C{arguments} (if any) to those specified at call time.  Here, C{callable_object}
        is usually a function or a method, but can in principle be anything callable,
        including an already existing binding.

        See also C{L{wrap}} class method for a different way of creating bindings.

        @raises TypeError: if C{callable_object} is not callable or C{arguments} is not
                           iterable.
        """

        if not callable (callable_object):
            raise TypeError ("`callable_object' must be callable")

        # This raises `TypeError' if `arguments' type is inappropriate.
        arguments = tuple (arguments)

        super (Binding, self).__init__()

        if isinstance (callable_object, BindingCompatibleTypes):
            self._object   = callable_object.im_self
            self._function = callable_object.im_func
            self._class    = callable_object.im_class
        else:
            self._object   = None
            self._function = callable_object
            self._class    = None

        self._arguments = arguments


    def wrap (_class, callable_object, arguments = ()):
        """
        Return a callable with semantics of the binding class this method is called for.
        I{If necessary} (e.g. if C{arguments} tuple is not empty), this method creates a
        binding instance first.  In any case, you can assume that returned object will
        I{behave} identically to an instance of this class with C{callable_object} and
        C{arguments} passed to C{L{__init__}} method.  However, the returned object I{is
        not required} to be an instance.

        This is the preferred method of creating bindings.  It is generally more memory-
        and call-time-efficient since in some cases no new objects are created at all.

        @rtype:            callable

        @raises TypeError: if C{callable_object} is not callable or C{arguments} is not
                           iterable.
        """

        if arguments is not ():
            return _class (callable_object, arguments)
        else:
            if not callable (callable_object):
                raise TypeError ("`callable_object' must be callable")

            return callable_object


    wrap = classmethod (wrap)


    def get_object (self):
        """
        Return object associated with this binding.  It is not C{None} only if binding is
        created for a bound method or another method with non-C{None} object.

        This method is analogous to C{L{im_self}} property.  Method is slightly faster,
        but the same property also exists for function and method objects, so the property
        is “standard interface”.

        @note:  Never override C{im_self} property, override this method instead.

        @rtype: object
        """

        return self._object

    def get_function (self):
        """
        Return raw function associated with this binding.

        This method is analogous to C{L{im_func}} property.  Method is slightly faster,
        but the same property also exists for function and method objects, so the property
        is “standard interface”.

        @note:  Never override C{im_func} property, override this method instead.

        @rtype: function
        """

        return self._function

    def get_class (self):
        """
        Return the class associated with this binding.

        This method is analogous to C{L{im_class}} property.  Method is slightly faster,
        but the same property also exists for function and method objects, so the property
        is “standard interface”.

        @note:  Never override C{im_class} property, override this method instead.

        @rtype: class or type
        """

        return self._class

    def get_arguments (self):
        """
        Get the arguments of this binding.  These are the arguments passed to
        C{L{__init__}} or C{L{wrap}} method.  When calling the binding, they are
        I{prepended} to arguments passed to C{L{__call__}}.

        There also exists C{L{im_args}} property, completely analogous to this method.
        Method is slightly faster, but the property is in line with standard C{L{im_self}}
        and other properties.

        @note:  Never override C{im_args} property, override this method instead.

        @rtype: tuple
        """

        return self._arguments


    def __call__(self, *arguments):
        """
        Call the wrapped callable (e.g. method or function) and return whatever it
        returns.  If binding was constructed with L{arguments <im_args>}, they are
        I{prepended} to arguments of this function before being passed to the wrapped
        callable.

        @rtype:            object
        @raises exception: whatever wrapped method raises, if anything.
        """

        # NOTE: If, for some reason, you change this, don't forget to adjust
        #       `WeakBinding.__call__' accordingly.
        if self.get_class () is not None:
            return self.get_function () (self.get_object (), *(self.get_arguments () + arguments))
        else:
            return self.get_function () (*(self.get_arguments () + arguments))


    def __eq__(self, other):
        """
        Determine if C{self} is equal to C{other}.  Two bindings are equal only if they
        wrap equal methods and have equal L{argument lists <im_args>}.  A binding with an
        empty argument list is also equal to its wrapped method or function.

        @rtype: bool
        """

        if self is other:
            return True

        if isinstance (other, BindingCompatibleTypes):
            if (   self.get_object   () is not other.im_self
                or self.get_function () is not other.im_func
                or self.get_class    () is not other.im_class):
                return False

            if isinstance (other, Binding):
                return self.get_arguments () == other.get_arguments ()
            else:
                return self.get_arguments () is ()

        else:
            if isinstance (other, types.FunctionType):
                return (self.im_func is other
                        and self.im_self is None
                        and self.im_class is None
                        and self.im_args is ())
            else:
                return NotImplemented



    def __ne__(self, other):
        """
        Determine if C{self} is not equal to C{other}.  See L{__eq__} for details.

        @rtype: bool
        """

        equal = self.__eq__(other)

        if equal is not NotImplemented:
            return not equal
        else:
            return NotImplemented


    def __nonzero__(self):
        """
        C{True} if binding is in its initial and fully functional state.  This method
        mainly exists for L{weak bindings <WeakBinding>}, for which it returns C{False}
        if binding’s object has been garbage-collected.

        @rtype:   bool
        @returns: Always C{True} for this class.
        """

        return True


    im_self  = property (lambda self: self.get_object (),
                         doc = ("""
                                The object of this binding or C{None} if it has been
                                garbage-collected already.  This property is provided
                                for consistency with similar property of plain methods.

                                @type: object

                                @note: Never override this property, override
                                       C{L{get_object}} method instead.
                                """))
    im_func  = property (lambda self: self.get_function (),
                         doc = ("""
                                Function of this binding.  This property is provided for
                                consistency with similar property of plain methods.

                                @type: function

                                @note: Never override this property, override
                                       C{L{get_function}} method instead.
                                """))
    im_class = property (lambda self: self.get_class (),
                         doc = ("""
                                Class of this binding’s object.  This property is provided
                                mainly for consistency with similar property of plain
                                methods.

                                @type: class or type

                                @note: Never override this property, override
                                       C{L{get_class}} method instead.
                                """))
    im_args  = property (lambda self: self.get_arguments (),
                         doc = ("""
                                Arguments of this binding as passed to C{L{__init__}} or
                                C{L{wrap}} method.  When calling the binding, they are
                                I{prepended} to arguments passed to C{L{__call__}}

                                This property is in line with standard C{L{im_self}} and
                                other properties.

                                @type: tuple

                                @note: Never override this property, override
                                       C{L{get_arguments}} method instead.
                                """))



BindingCompatibleTypes = (types.MethodType, Binding)



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

        - C{L{get_object}} returns C{None} (and C{L{im_self}} is equal to C{None},
          accordingly);

        - boolean state (see C{L{__nonzero__}} method) of the binding becomes C{False}.

    @see:  RaisingWeakBinding
    """

    __slots__ = ('_WeakBinding__callback')


    def __init__(self, callable_object, arguments = (), callback = None):
        """
        Initialize a new weak binding which will call C{callable_object}, I{prepending}
        fixed C{arguments} (if any) to those specified at call time.  Here,
        C{callable_object} is usually a function or a method, but can in principle be
        anything callable, including an already existing binding.

        If C{callable_object} is a bound method, its object is referenced weakly.  It is
        also legal to create weak bindings for other callables, but they will behave
        identically to plain bindings in that case.

        See also C{L{wrap}} class method for a different way of creating weak bindings.

        @raises TypeError:                if C{callable_object} is not callable or
                                          C{arguments} is not iterable.
        @raises CannotWeakReferenceError: if C{callable_object} is a bound method, but
                                          its object is not weakly referencable.
        """

        super (WeakBinding, self).__init__(callable_object, arguments)

        if self._object is not None:
            if callback is not None and not callable (callback):
                raise TypeError ("`callback' must be callable")

            try:
                self.__callback = callback
                self._object    = weakref.ref (self._object, self.__object_garbage_collected)
            except:
                raise CannotWeakReferenceError (self._object)
        else:
            self._object = _NONE_REFERENCE


    def wrap (_class, callable_object, arguments = (), callback = None):
        # Inherit documentation somehow?
        if (arguments is not ()
            or (    isinstance (callable_object, BindingCompatibleTypes)
                and not isinstance (callable_object, WeakBinding)
                and callable_object.im_self is not None)):
            return _class (callable_object, arguments, callback)
        else:
            return callable_object


    wrap = classmethod (wrap)


    def get_object (self):
        """
        Return object associated with this binding.  It is not C{None} only if binding is
        created for a bound method or another method with non-C{None} object I{or} the
        object was not C{None}, but has been garbage-collected.

        This method is analogous to C{L{im_self}} property.  Method is slightly faster,
        but the same property also exists for function and method objects, so the property
        is “standard interface”.

        @note:  Never override C{im_self} property, override this method instead.

        @rtype: object
        """

        reference = self._object

        if reference is not None:
            return reference ()
        else:
            return None


    def __call__(self, *arguments):
        """
        Like L{Binding.__call__}, but account for garbage-collected objects.  If object
        has been garbage-collected, then do nothing and return C{None}.

        @rtype:            object
        @raises exception: whatever wrapped method raises, if anything.
        """

        reference = self._object

        if reference is not None:
            # NOTE: This is essentially inlined method of the superclass.  While calling
            #       that method would be more proper, inlining it gives significant speed
            #       improvement.  Since it makes no difference for derivatives, we
            #       sacrifice "do what is right" principle in this case.

            if self.get_class () is not None:
                return self.get_function () (reference (), *(self.get_arguments () + arguments))
            else:
                return self.get_function () (*(self.get_arguments () + arguments))
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

        @rtype: object
        """

        return None


    def __object_garbage_collected (self, reference):
        self._object = None

        callback = self.__callback
        if callback is not None:
            self.__callback = None
            callback (reference)


    def __nonzero__(self):
        """
        C{True} if method’s object hasn’t been garbage-collected.  More precisely, C{True}
        if binding is in its initial and fully functional state, but for weak bindings it
        means exactly what is stated in the previous statement.

        @rtype: bool
        """

        return self._object is not None


_NONE_REFERENCE = DummyReference (None)



class RaisingWeakBinding (WeakBinding):

    """
    A variation of L{weak binding <WeakBinding>} which raises C{L{GarbageCollectedError}}
    if called after its object has been garbage-collected.  There are no other difference
    from common weak bindings.  In particular, if a binding is create without an object
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
    Exception thrown when calling an instance of L{RaisingWeakBinding} with a
    garbage-collected object.
    """

    pass



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
