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
A collection of utilities that can also be used from outside, if wanted.  Functions and
classes here can be assumed public and won’t disappear in future Py-notify versions.
"""

__docformat__ = 'epytext en'
__all__       = ('raise_not_implemented_exception',
                 'is_valid_identifier',
                 'DummyReference')


import re
import sys



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



def is_valid_identifier (identifier):
    """
    Determine if C{identifier} is a valid Python identifier.  This function never raises
    any exceptions.  If C{identifier} is not a string, it simply returns C{False}.

    @param identifier: identifier to determin if it is valid
    @type  identifier: C{basestring}

    @rtype:            C{bool}
    """

    return (isinstance (identifier, basestring)
            and re.match ('^[_a-zA-Z][_a-zA-Z0-9]*$', identifier) is not None)



class DummyReference (object):

    """
    Simple class that is interface-compatible with C{weakref.ReferenceType}.  In other
    words, its constructor accepts only one parameter and this value is later returned
    from C{L{__call__}} method.  Unlike weak references, instances of this class don’t do
    anything special.  They are only needed to avoid special cases for non-references,
    since you can treat instances of C{weakref.ReferenceType} and this class in the same
    way.
    """

    __slots__ = ('_DummyReference__object')


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



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
