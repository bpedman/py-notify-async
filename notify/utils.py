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
A collection of utilities that can also be used from outside, if needed.
"""

__docformat__ = 'epytext en'
__all__       = ('raise_not_implemented_exception',
                 'is_valid_identifier',
                 'DummyReference')


import re



def raise_not_implemented_exception (object = None):

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

    @raises NotImplementedError: always.
    """

    import sys

    function_name        = None
    function_description = 'UNKNOWN FUNCTION'

    try:
        raise Exception
    except:
        try:
            traceback            = sys.exc_info () [2]
            function_name        = traceback.tb_frame.f_back.f_code.co_name
            function_description = '%s()' % function_name
        except:
            # We can do nothing, ignore.
            pass

    try:
        class_description = ' in class %s' % object.__class__.__name__

        if function_name:
            declaration_classes = _find_declaration_classes (object.__class__, function_name)

            if len (declaration_classes) == 1:
                if declaration_classes[0] is not object.__class__:
                    class_description += ' (declared in %s)' % declaration_classes[0].__name__

            elif len (declaration_classes) > 1:
                class_description += (' (declared in %s)'
                                      % ', '.join (map (lambda _class: _class.__name__,
                                                        declaration_classes)))

    except:
        class_description = ""

    exception = NotImplementedError ('%s not implemented%s'
                                     % (function_description, class_description))
    raise exception


def _find_declaration_classes (_class, function_name):
    declaring_bases = filter (lambda base: hasattr (base, function_name), _class.__bases__)

    if declaring_bases:
        return reduce (lambda list1, list2: list1 + list2,
                       map (_find_declaration_classes,
                            declaring_bases, (function_name,) * len (declaring_bases)),
                       [])
    else:
        return [_class]



def is_valid_identifier (identifier):
    return (isinstance (identifier, basestring)
            and re.match ('^[_a-zA-Z][_a-zA-Z0-9]*$', identifier) is not None)



class DummyReference (object):

    __slots__ = ('_DummyReference__object')


    def __init__ (self, object):
        self.__object = object

    def __call__ (self):
        return self.__object



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
