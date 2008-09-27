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
Mediators can be used to transform values from one format to another and back.  Main
advantage over transformation ‘by hands’ is that both ‘to’ and ‘from’ transformations are
encapsulated in one object and are not separated from each other.

If two mediators are equal and C{L{AbstractMediator.forward}} or
C{L{AbstractMediator.back}} are called with equal functions on each of the two, resulting
callables will be equal.  This may be not easy to achive with simple functions when you
need transformation to depend on a parameter:

    >>> f1 = lambda x: x + 10
    ... f2 = lambda x: x + 10
    ... f1 != f2
    ...
    ... import operator
    ... from notify.mediator import *
    ... identity = lambda x: x
    ... m1 = FunctionalMediator (operator.add, operator.sub, 10)
    ... m2 = FunctionalMediator (operator.add, operator.sub, 10)
    ... m1 == m2
    ... m1.forward (identity) == m2.forward (identity)

This property is important when using C{L{Signal.disconnect <signal.Signal.disconnect>}}
or one of the functions that base on it.  Since it disconnects an I{equal} (not identical)
handler, with mediators you can avoid storing handler around: an equal one can be
constructed when needed.  When using lambdas, you’d have to store handler.

G{classtree AbstractMediator}
"""

__docformat__ = 'epytext en'
__all__       = ('AbstractMediator', 'BooleanMediator', 'FunctionalMediator')


from notify.utils import is_callable, raise_not_implemented_exception



#-- Base mediator class ----------------------------------------------

class AbstractMediator (object):

    """
    An abstract object that can transform values between two formats (back and forth).  In
    addition, it can create proxies for arbitrary functions with C{L{forward}} and
    C{L{back}} methods.  When a proxy is called with single value, the value is
    transformed forth or back first, and then passed to underlying function.

    In other words, proxies work in such a way that
        >>> mediator.forward (some_function) (value)

    is the same as
        >>> some_function (mediator.forward_value (value))

    Former expression is somewhat more cryptic and generally should not be used when you
    just need to convert I{one} value.  However, it (without the last call) can be exactly
    what is needed to create an argument to a L{signal}.
    """

    __slots__ = ()


    def forward_value (self, value):
        """
        Apply forward transformation to C{value} and return the result.  This function may
        raise any exception if mediator imposes some restrictions on C{value} and it
        doesn’t satisfy them.

        @rtype: C{object}
        """

        raise_not_implemented_exception (self)

    def back_value (self, value):
        """
        Apply back transformation to C{value} and return the result.  This function may
        raise any exception if mediator imposes some restrictions on C{value} and it
        doesn’t satisfy them.

        @rtype: C{object}
        """

        raise_not_implemented_exception (self)


    def forward (self, function):
        """
        Return a callable accepting one argument that applies forward transformation to it
        and passes result to C{function}.  It holds that if C{m1} and C{m2} are two equal
        mediators and C{f1} and C{f2} are two equal callables (e.g. functions), then:

            >>> m1.forward (f1) == m2.forward (f2)

        In addition to that, for any C{value} to which forward transformation can be
        applied,

            >>> m1.forward (f1) (value) == m2.forward (f2) (value) == m1.forward_value (value)


        @rtype:            callable

        @raises TypeError: if C{function} is not callable.
        """

        if is_callable (function):
            return _Forward (self, function)
        else:
            raise TypeError ("'function' must be callable")

    def back (self, function):
        """
        Return a callable accepting one argument that applies back transformation to it
        and passes result to C{function}.  It holds that if C{m1} and C{m2} are two equal
        mediators and C{f1} and C{f2} are two equal callables (e.g. functions), then:

            >>> m1.back (f1) == m2.back (f2)

        In addition to that, for any C{value} to which back transformation can be applied,

            >>> m1.back (f1) (value) == m2.back (f2) (value) == m1.back_value (value)


        @rtype:            callable

        @raises TypeError: if C{function} is not callable.
        """

        if is_callable (function):
            return _Back (self, function)
        else:
            raise TypeError ("'function' must be callable")


    def reverse (self):
        """
        Return a mediator that does exactly opposite transformations.  More specifically,
        if C{m2 = m1.reverse ()}, then:

            >>> m1.forward_value (value)    == m2.back_value    (value)
            ... m1.back_value    (value)    == m2.forward_value (value)
            ... m1.forward       (function) == m2.back          (function)
            ... m1.back          (function) == m2.forward       (function)

        Additionaly, it holds that C{mediator.reverse ().reverse () == mediator}.
        However, there are no guarantees on type (or even identity) of the returned value
        except those mentioned above and that it is an instance of the C{AbstractMediator}
        class.

        @rtype: C{AbstractMediator}
        """

        return _ReverseMediator (self)


    # Note: only present as a means for stating that ``mediators are comparable.''
    def __eq__(self, other):
        """
        Determine if two mediators are equal.  This function is not required to catch all
        possible cases of equal mediators, as, for instance, determine equality of
        mediators of different classes is often very difficult, if not impossible.
        However, it should—as much as (efficiently) possible—detect equal mediators of the
        same class.

        @rtype: C{bool}
        """

        return self is other

    def __ne__(self, other):
        """
        Determine if two mediators are not equal.  See C{L{__eq__}} for details.

        @rtype: C{bool}
        """

        equal = self.__eq__(other)

        if equal is not NotImplemented:
            return not equal
        else:
            return NotImplemented



#-- Standard mediator classes ----------------------------------------

class BooleanMediator (AbstractMediator):

    """
    A mediator that transforms C{true_value} and C{false_value} to C{True} and C{False}
    correspondingly.  Other values are transformed using C{fallback} function to C{True}
    or C{False}, depending on C{bool} result over C{fallback}’s return value.  Back
    transformation is like this: logically true values are transformed to C{true_value},
    logically false ones—to C{false_value}.

    It may be more understandable from an example:

        >>> mediator = BooleanMediator ('apple', 'orange', lambda x: isinstance (x, str))
        ...
        ... mediator.forward_value ('apple')  == True
        ... mediator.forward_value ('orange') == False
        ... mediator.forward_value ('')       == True
        ... mediator.forward_value (15)       == False
        ...
        ... mediator.back_value    (True)     == 'apple'
        ... mediator.back_value    (False)    == 'orange'
        ... mediator.back_value    (15)       == 'apple'
    """

    __slots__ = ('__true_value', '__false_value', '__fallback')


    def __init__(self, true_value = True, false_value = False, fallback = None):
        if fallback is None:
            fallback = bool
        else:
            if not is_callable (fallback):
                raise TypeError ("'fallback' must be a callable")

        super (BooleanMediator, self).__init__()

        self.__true_value  = true_value
        self.__false_value = false_value
        self.__fallback    = fallback


    def forward_value (self, value):
        if value == self.__true_value:
            return True
        elif value == self.__false_value:
            return False
        else:
            return bool (self.__fallback (value))


    def back_value (self, value):
        if value:
            return self.__true_value
        else:
            return self.__false_value


    def __eq__(self, other):
        if isinstance (other, BooleanMediator):
            return (    self.__true_value  == other.__true_value
                    and self.__false_value == other.__false_value
                    and self.__fallback    == other.__fallback)
        else:
            return NotImplemented

    def __hash__(self):
        return hash (self.__true_value) ^ hash (self.__false_value) ^ hash (self.__fallback)



class FunctionalMediator (AbstractMediator):

    """
    A mediator that delegates forward and back transformations to arbitrary functions
    (actually, anything callable.)
    """

    __slots__ = ('__forward_function', '__back_function', '__arguments', '__keywords')


    def __init__(self, forward_function = None, back_function = None, *arguments, **keywords):
        if (   not (forward_function is None or is_callable (forward_function))
            or not (back_function    is None or is_callable (back_function))):
            raise TypeError ('both functions must be callable or None')

        super (FunctionalMediator, self).__init__()

        self.__forward_function = forward_function or _identity
        self.__back_function    = back_function    or _identity
        self.__arguments        = arguments
        self.__keywords         = keywords


    def forward_value (self, value):
        return self.__forward_function (value, *self.__arguments, **self.__keywords)

    def back_value (self, value):
        return self.__back_function (value, *self.__arguments, **self.__keywords)


    def reverse (self):
        """
        Return a mediator that does exactly opposite transformations.
        """

        return self.__class__(self.__back_function, self.__forward_function,
                              *self.__arguments, **self.__keywords)


    def __eq__(self, other):
        if isinstance (other, FunctionalMediator):
            return (self    .__forward_function == other.__forward_function
                    and self.__back_function    == other.__back_function
                    and self.__arguments        == other.__arguments
                    and self.__keywords         == other.__keywords)
        else:
            return NotImplemented

    def __hash__(self):
        return (hash   (self.__forward_function)
                ^ hash (self.__back_function)
                ^ hash (self.__arguments)
                ^ hash (self.__keywords))



def _identity (value, *ignored_arguments, **ignored_keywords):
    return value



#-- Internal mediator and related classes ----------------------------

class _ReverseMediator (AbstractMediator):

    __slots__ = ('__wrapped_mediator')


    def __init__(self, wrapped_mediator):
        super (_ReverseMediator, self).__init__()
        self.__wrapped_mediator = wrapped_mediator


    def forward_value (self, value):
        return self.__wrapped_mediator.back_value (value)

    def back_value (self, value):
        return self.__wrapped_mediator.forward_value (value)


    def forward (self, function):
        return self.__wrapped_mediator.back (function)

    def back (self, function):
        return self.__wrapped_mediator.forward (function)


    def reverse (self):
        return self.__wrapped_mediator


    def __eq__(self, other):
        if isinstance (other, _ReverseMediator):
            return self.__wrapped_mediator == other.__wrapped_mediator
        else:
            return NotImplemented

    def __hash__(self):
        return ~hash (self.__wrapped_mediator)



class _Function (object):

    __slots__ = ('_mediator', '_function')


    def __init__(self, mediator, function):
        super (_Function, self).__init__()

        self._mediator = mediator
        self._function = function



    def __eq__(self, other):
        return (    self.__class__ is other.__class__
                and self._mediator == other._mediator
                and self._function == other._function)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash (type (self)) ^ hash (self._mediator) ^ hash (self._function)



class _Forward (_Function):

    def __call__(self, value):
        return self._function (self._mediator.forward_value (value))



class _Back (_Function):

    def __call__(self, value):
        return self._function (self._mediator.back_value (value))



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
