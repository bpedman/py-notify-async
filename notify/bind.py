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



#-- Base binding class -----------------------------------------------

class Binding (object):

    """
    Bindings are sort of callables with advanced comparing capabilities.
    """

    __slots__ = ('_object', '_function', '_class', '_arguments')


    def __init__(self, callable_object, arguments = ()):
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
        if arguments is not ():
            return _class (callable_object, arguments)
        else:
            return callable_object


    wrap = classmethod (wrap)


    def __call__(self, *arguments):
        """
        Call the wrapped plain method or function and return whatever it returns.  If
        binding was constructed with arguments, they are I{prepended} to arguments of this
        function before being passed to wrapped method or function.

        @rtype:            object
        @raises exception: whatever wrapped method raises, if anything.
        """

        if self.im_class is not None:
            return self.im_func (self.im_self, *(self.im_args + arguments))
        else:
            return self.im_func (*(self.im_args + arguments))


    def __eq__(self, other):
        """
        Determine if C{self} is equal to C{other}.  Two weak methods wrapping are equal
        only if they wrap equal methods.  A weak method is also equal to its wrapped plain
        method.

        @rtype: bool
        """

        if self is other:
            return True

        if not isinstance (other, BindingCompatibleTypes):
            return False

        if (   self.im_self  is not other.im_self
            or self.im_func  is not other.im_func
            or self.im_class is not other.im_class):
            return False

        if isinstance (other, Binding):
            return self.im_args == other.im_args
        else:
            return self.im_args is ()


    def __ne__(self, other):
        """
        Determine if C{self} is not equal to C{other}.  See L{__eq__} for details.

        @rtype: bool
        """

        return not self.__eq__(other)


    def __nonzero__(self):
        """
        C{True} if method’s object hasn’t been garbage-collected.

        @rtype: bool
        """

        return True

    def __hash__(self):
        """
        Hash code, equal to those of the wrapped method.  If object has been
        garbage-collected, hash code of the corresponding unbound method instead.

        @rtype: int
        """

        # FIXME: I'm not sure it is not a hack...
        _hash     = hash (types.MethodType (self.im_func, self.im_self, self.im_class))
        arguments = self.im_args

        if arguments:
            _hash += 31 * hash (arguments)

        return _hash



    im_self  = property (lambda self: self._object,
                         doc = ("""
                                The object of this weak method or C{None} if it has been
                                garbage-collected already.  This property is provided
                                mainly for consistency with similar property of plain
                                methods.

                                @type: object
                                """))
    im_func  = property (lambda self: self._function,
                         doc = ("""
                                Function of this weak method.  This property is provided
                                mainly for consistency with similar property of plain
                                methods.

                                @type: function
                                """))
    im_class = property (lambda self: self._class,
                         doc = ("""
                                Class of this weak method.  This property is provided
                                mainly for consistency with similar property of plain
                                methods.

                                @type: class or type
                                """))
    im_args  = property (lambda self: self._arguments,
                         doc = ("""
                                Class of this weak method.  This property is provided
                                mainly for consistency with similar property of plain
                                methods.

                                @type: class or type
                                """))



BindingCompatibleTypes = (types.MethodType, Binding)



#-- Weak binding classes ---------------------------------------------

class WeakBinding (Binding):

    __slots__ = ()


    def __init__(self, callable_object, arguments = (), callback = None):
        super (WeakBinding, self).__init__(callable_object, arguments)

        if self._object is not None:
            if callback is not None and not callable (callback):
                raise TypeError ("`callback' must be callable")

            try:
                self._object = weakref.ref (self._object, callback)
            except:
                raise CannotWeakReferenceError (self._object)


    def wrap (_class, callable_object, arguments = (), callback = None):
        if (arguments is not ()
            or (    isinstance (callable_object, BindingCompatibleTypes)
                and not isinstance (callable_object, WeakBinding)
                and callable_object.im_self is not None)):
            return _class (callable_object, arguments, callback)
        else:
            return callable_object


    wrap = classmethod (wrap)


    def __call__(self, *arguments):
        """
        Like L{Binding.__call__}, but account for garbage-collected objects.  If object
        has been garbage-collected, then do nothing and return C{None}.

        @rtype:            object
        @raises exception: whatever wrapped method raises, if anything.
        """

        reference = self._object

        if reference is not None:
            object = reference ()
            if object is None:
                return self._call_after_garbage_collecting ()

        return super (WeakBinding, self).__call__(*arguments)


    def _call_after_garbage_collecting (self):
        return None


    def __nonzero__(self):
        """
        C{True} if method’s object hasn’t been garbage-collected.

        @rtype: bool
        """

        reference = self._object
        return reference is None or reference () is not None


    def __get_object (self):
        reference = self._object

        if reference is not None:
            return reference ()
        else:
            return None


    im_self  = property (__get_object,
                         doc = ("""
                                The object of this weak method or C{None} if it has been
                                garbage-collected already.  This property is provided
                                mainly for consistency with similar property of plain
                                methods.

                                @type: object
                                """))



class RaisingWeakBinding (WeakBinding):

    """
    """

    __slots__    = ()


    def _call_after_garbage_collecting (self):
        raise GarbageCollectedError



#-- Exception types for weak bindings --------------------------------

class CannotWeakReferenceError (TypeError):

    """
    Exception thrown when trying to create a weak binding for an object that doesn’t
    support weak references.
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
