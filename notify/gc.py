# -*- coding: utf-8 -*-

#--------------------------------------------------------------------#
# This file is part of Py-notify.                                    #
#                                                                    #
# Copyright (C) 2007, 2008 Paul Pogonyshev.                          #
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
A module for protecting objects from garbage collector.  Sometimes, objects that don’t
have a reference to them (and so are valid garbage collector targets) need to stay alive.
Good example of this are logic L{conditions <condition>}: their state can change because
they have term conditions, yet they may be not referenced from anywhere, since handlers
don’t need a reference to notice a state change.

This module defines both a simple L{interface <AbstractGCProtector>} and several
implementations, some, which are suitable for production use (C{L{FastGCProtector}}), some
for debugging purposes (C{L{RaisingGCProtector}}, C{L{DebugGCProtector}}.)

Py-notify classes use value of the C{AbstractGCProtector.default} variable as the
protector instance.  In case you run into a problem, set it to an instance of
C{DebugGCProtector} or a similar class to track the problem down (somewhere near your
program beginning).  However, we believe that Py-notify classes must not cause problems
themselves, they may pop up only if you use a garbage-collection protector yourself.
"""

__docformat__ = 'epytext en'
__all__       = ('GCProtectorMeta', 'AbstractGCProtector', 'StandardGCProtector',
                 'SlowGCProtector',
                 'HAVE_FAST_IMPLEMENTATIONS',
                 'FastGCProtector', 'RaisingGCProtector', 'DebugGCProtector')


from notify.utils import _PYTHON_IMPLEMENTATION, raise_not_implemented_exception



class GCProtectorMeta (type):

    """
    A meta-class for C{L{AbstractGCProtector}}.  Its only purpose is to define
    C{L{default}} property of the class.  In principle, it can be used for your classes
    too, but better subclass C{AbstractGCProtector} instead.
    """

    def _get_default (self):
        return _default

    def _set_default (self, default):
        global _default
        if default is _default:
            return

        if not isinstance (default, AbstractGCProtector):
            raise ValueError ('can only set AbstractGCProtector.default to an instance of '
                              'AbstractGCProtector; got %s instead' % type (_default))

        try:
            num_active_protections = _default.num_active_protections
        except AttributeError:
            num_active_protections = None

        if num_active_protections:
            raise ValueError ('cannot set a different GC protector: current has active protections '
                              '(num_active_protections = %s)' % num_active_protections)

        _default = default


    default = property (_get_default, _set_default,
                        doc = ("""
                               Current default GC protector.  Starts out as an instance of
                               C{L{FastGCProtector}}, but can be changed for debugging
                               purposes.  Note that setting this class property is only
                               possible if current default protector doesn’t have any
                               active protections, i.e. if its C{num_active_protections}
                               property is zero (or has any false truth value).  This is
                               generally true only at the start of the program, so you
                               cannot arbitrarily switch protectors.  Doing so would lead
                               to unpredictable consequences, up to crashing the
                               interpreter, therefore the restriction.
                               """))


    del _get_default, _set_default



def protect (self, object):
    """
    Protect C{object} from being garbage-collected.  It is legal to protect same C{object}
    several times and an object is prevented from being garbage-collected if it has been
    protected at least once.  As a special case, if C{object} is C{None}, this function
    does nothing.

    For convenience, this function always returns C{object} itself.

    @rtype: C{object}
    """

    raise_not_implemented_exception (self)

def unprotect (self, object):
    """
    Unprotect C{object}.  If has been protected once only or exactly one time more than
    times it has been unprotected, make it a legal target for garbage collection again.
    It is an error to call C{unprotect} more times than C{protect} for a same object, and
    descendant behaviour in this case is undefined.  It may even crash Python.  However,
    as a special case, if C{object} is C{None}, this function does nothing.  In
    particular, it is legal to ‘unprotect’ C{None} without having protected it first,
    because it will be a no-op and not lead to bugs.

    For convenience, this function always returns C{object} itself.

    @rtype: C{object}
    """

    raise_not_implemented_exception (self)

def set_default (self, default):
    """
    This method is deprecated.  Instead, set C{AbstractGCProtector.default} directly.
    """

    AbstractGCProtector.default = default



# This weird class creation only to workaround differences in specifying metaclass between
# Python 2.x and 3.x.
AbstractGCProtector = GCProtectorMeta ('AbstractGCProtector', (object,),
                                       { 'protect':     protect,
                                         'unprotect':   unprotect,
                                         'set_default': set_default })

AbstractGCProtector.__doc__ = \
"""
Simple protector interface with two methods for implementations to define.
"""

del protect, unprotect, set_default



class SlowGCProtector (AbstractGCProtector):

    def __init__(self):
        self.__protected_objects = { }


    def protect (self, object):
        if object is not None:
            object_id         = id (object)
            protected_objects = self.__protected_objects
            protection_data   = protected_objects.get (object_id)

            if protection_data is None:
                protected_objects[object_id] = (object, 1)
            else:
                protected_objects[object_id] = (object, protection_data[1] + 1)

        return object

    def unprotect (self, object):
        if object is not None:
            object_id         = id (object)
            protected_objects = self.__protected_objects
            protection_data   = protected_objects.get (object_id)

            if protection_data is not None:
                num_object_protections = protection_data[1]
                if num_object_protections == 1:
                    del protected_objects[object_id]
                else:
                    protected_objects[object_id] = (object, num_object_protections - 1)
            else:
                raise UnprotectionError ('object is not protected by this %s' % type (self))

        return object


    def num_protected_objects (self):
        return len (self.__protected_objects)

    def num_active_protections (self):
        num_active_protections = 0
        for object, num_object_protections in self.__protected_objects.values ():
            num_active_protections += num_object_protections

        return num_active_protections

    num_protected_objects  = property (num_protected_objects)
    num_active_protections = property (num_active_protections)


    def get_num_object_protections (self, object):
        if object is not None:
            protection_data = self.__protected_objects.get (id (object))
            if protection_data is not None:
                return protection_data[1]

        return 0



class UnprotectionError (ValueError):

    """
    Error that is raised by some L{garbage-collection protectors <AbstractGCProtector>}
    when you try to L{unprotect <AbstractGCProtector.unprotect>} an object more times than
    it had been L{protected <AbstractGCProtector.protect>}.  Of the standard protectors
    only C{L{RaisingGCProtector}} ever raises these exceptions.
    """


if _PYTHON_IMPLEMENTATION == 'CPython':
    from notify._gc import DebugGCProtector, FastGCProtector, RaisingGCProtector

    StandardGCProtector       = FastGCProtector
    HAVE_FAST_IMPLEMENTATIONS = True

else:
    StandardGCProtector       = SlowGCProtector
    HAVE_FAST_IMPLEMENTATIONS = False


_default = StandardGCProtector ()



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
