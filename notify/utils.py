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
A collection of utilities that can also be used from outside, if wanted.  Functions and
classes here can be assumed public and won’t disappear in future Py-notify versions.

@var is_callable:
Determine if C{object} is callable.  E.g. if it is a function, method, class, instance of
a class with C{__call__}, etc.  This is the same as built-in function C{callable} does.
C{is_callable} is provided since C{callable} is going to disappear in Python 3000 and may
issue warnings in 2.6.

@var as_string:
Convert any attribute to its name as string.  Main use of this utility object is to
perform Python ‘private’ identifier mangling.  E.g. you can write::

    class MyClass (object):
        __slots__ = ('__x')
        def get_x (self):
            if hasattr (self, as_string.__x):
                return self.__x

Advantage is that you don’t have to do mangling ‘by hands’ and hence there is less chance
for a typing error.  Furthermore, this code does not require changes if you change
C{MyClass} name to anything else, whereas custom mangling does.

However, usefulness of ‘as_string’ is still doubtful.  When I wrote it, I didn’t know one
could just write ``__slots__ = ('__x')``, I thought it needed to be
``__slots__ = ('_MyClass__x')``.  Imagine...
"""

__docformat__ = 'epytext en'
__all__       = ('is_callable', 'is_valid_identifier', 'mangle_identifier',
                 'as_string',
                 'raise_not_implemented_exception',
                 'execute',
                 'frozendict', 'DummyReference', 'ClassTypes', 'StringType')


import re
import sys
import types
from keyword import iskeyword



if sys.version_info[:3] < (2, 6, 0):
    is_callable = callable

else:
    def is_callable (object):
        return hasattr (object, '__call__')



def is_valid_identifier (identifier):
    """
    Determine if C{identifier} is a valid Python identifier.  This function never raises
    any exceptions.  If C{identifier} is not a string, it simply returns C{False}.

    @param identifier: identifier to determin if it is valid
    @type  identifier: C{basestring}

    @rtype:            C{bool}
    """

    return (isinstance (identifier, StringType)
            and re.match ('^[_a-zA-Z][_a-zA-Z0-9]*$', identifier) is not None
            and not iskeyword (identifier))


def mangle_identifier (class_name, identifier):
    """
    Mangle C{identifier} as how would be done if it appeared in a class with
    C{class_name}.  This function allows to mimic standard Python mangling of
    pseudo-private attributes, i.e. those which names start with two underscores and don’t
    end in two.  If C{identifier} is not considered a private name, it is returned
    unchanged.

    @param  class_name: name of Python class.
    @type   class_name: C{basestring}

    @param  identifier: name of an attribute of that class.
    @type   identifier: C{basestring}

    @rtype: C{str}

    @raises ValueError: if either C{class_name} or C{identifier} is not valid from
                        Python’s point of view.
    """

    if not (is_valid_identifier (class_name) and is_valid_identifier (identifier)):
        raise ValueError ("'class_name' and 'identifier' must be valid Python identifiers")

    if (identifier.startswith ('__')
        and not identifier.endswith ('__')
        and class_name != '_' * len (class_name)):
        return '_%s%s' % (class_name.lstrip ('_'), identifier)
    else:
        return identifier



class _AsString (object):

    """
    Internal helper class for C{L{as_string}}.  Don’t use directly.
    """

    __slots__ = ()

    def __getattribute__(self, name):
        return name

    def __setattr__(self, name, value):
        raise TypeError ("'as_string' attributes cannot be set")

    def __delattr__(self, name):
        raise TypeError ("'as_string' attributes cannot be deleted")

    def __repr__(self):
        return 'notify.utils.as_string'


as_string = _AsString ()



def raise_not_implemented_exception (object = None, function_name = None):
    """
    Raise C{NotImplementedError} for a method invoked with C{object} as C{self}.  The
    function determines object class and method declaration class(es) itself and that’s
    the whole point of it.

    It should be called like this:
        >>> raise_not_implemented_exception (self)

    And output might look like this::
       File ".../foo.py", line # in ?
         Foo ().bar ()
       File ".../foo.py", line #, in bar
         raise_not_implemented_exception (self)
       File ".../notify/utils.py", line #, in raise_not_implemented_exception
         raise exception
     NotImplementedError: bar() not implemented in class Foo (declared in AbstractFoo)

    Optionally, C{function_name} can be specified.  This argument mainly exists for C
    extension, since function name cannot be detected automatically in this case.  In
    Python code you should just leave this argument out.

    @param  object:              the object for which a non-implemented method is called.
    @type   object:              C{object}

    @param  function_name:       name of the unimplemented function or method (inferred
                                 automatically for non-extension functions).
    @type   function_name:       C{basestring} or C{None}

    @raises NotImplementedError: always.
    """

    if function_name is None:
        try:
            raise Exception
        except Exception:
            try:
                traceback     = sys.exc_info () [2]
                function_name = traceback.tb_frame.f_back.f_code.co_name
            except Exception:
                # We can do nothing, ignore.
                pass

    if function_name is not None:
        function_description = '%s()' % function_name
    else:
        function_description = 'UNKNOWN FUNCTION'

    try:
        class_description = ' in class %s' % object.__class__.__name__

        if function_name is not None:
            declaration_classes = _find_declaration_classes (object.__class__, function_name)

            if len (declaration_classes) == 1:
                if declaration_classes[0] is not object.__class__:
                    class_description += ' (declared in %s)' % declaration_classes[0].__name__

            elif len (declaration_classes) > 1:
                class_description += (' (declared in %s)'
                                      % ', '.join ([_class.__name__
                                                    for _class in declaration_classes]))

    except Exception:
        class_description = ''

    exception = NotImplementedError ('%s not implemented%s'
                                     % (function_description, class_description))
    raise exception


def _find_declaration_classes (_class, function_name):
    declaring_bases = [base for base in _class.__bases__ if hasattr (base, function_name)]

    if declaring_bases:
        return reduce (lambda list1, list2: list1 + list2,
                       [_find_declaration_classes (base, function_name)
                        for base in declaring_bases],
                       [])
    else:
        return [_class]


if sys.version_info[0] >= 3:
    execute = eval ('exec')
else:
    from notify._2_x import execute



class frozendict (dict):

    __slots__ = ('__hash')

    def __init__(self, *arguments, **keywords):
        super (frozendict, self).__init__(*arguments, **keywords)
        self.__hash = None


    def clear (self):
        raise TypeError ("'%s' object doesn't support clearing" % type (self).__name__)

    def pop (self, key, default = None):
        raise TypeError ("'%s' object doesn't support popping" % type (self).__name__)

    def popitem (self):
        raise TypeError ("'%s' object doesn't support popping" % type (self).__name__)

    def setdefault (self, key, default = None):
        raise TypeError ("'%s' object doesn't support setdefault operation" % type (self).__name__)

    def update (self, dict):
        raise TypeError ("'%s' object doesn't support updating" % type (self).__name__)


    def __setitem__(self, key, value):
        raise TypeError ("'%s' object doesn't support item setting" % type (self).__name__)

    def __delitem__(self, key):
        raise TypeError ("'%s' object doesn't support item deletion" % type (self).__name__)


    def __hash__(self):
        _hash = self.__hash

        if _hash is None:
            _hash = 0x1337

            if hasattr (dict, 'iteritems'):
                for key, value in self.iteritems ():
                    _hash ^= hash (key) ^ hash (value)
            else:
                for key, value in self.items ():
                    _hash ^= hash (key) ^ hash (value)

            self.__hash = _hash

        return _hash


    def __repr__(self):
        return '%s (%s)' % (type (self).__name__, super (frozendict, self).__repr__())



frozendict.EMPTY = frozendict ({ })
# Force hash to be precomputed.
hash (frozendict.EMPTY)



class DummyReference (object):

    """
    Simple class that is interface-compatible with C{weakref.ReferenceType}.  In other
    words, its constructor accepts only one parameter and this value is later returned
    from C{L{__call__}} method.  Unlike weak references, instances of this class don’t do
    anything special.  They are only needed to avoid special cases for non-references,
    since you can treat instances of C{weakref.ReferenceType} and this class in the same
    way.
    """

    __slots__ = ('__object')


    def __init__(self, object):
        """
        Create a new dummy reference that will return C{object} when called.

        @param object: the object that will be returned by this reference.
        @type  object: C{object}
        """

        self.__object = object

    def __call__(self):
        """
        Return the C{object} specified at construction time.

        @rtype: C{object}
        """

        return self.__object


    def __repr__(self):
        return ('<%s.%s at 0x%x; to %r>'
                % (self.__module__, self.__class__.__name__, id (self), self.__object))

    def __str__(self):
        return '<%s at 0x%x; to %s>' % (self.__class__.__name__, id (self), self.__object)


if sys.version_info[0] >= 3:
    ClassTypes = (type,)
    StringType = str
else:
    ClassTypes = (type, types.ClassType)
    StringType = basestring



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
