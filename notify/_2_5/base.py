# -*- coding: utf-8 -*-

#--------------------------------------------------------------------#
# This file is part of Py-notify.                                    #
#                                                                    #
# Copyright (C) 2007 Paul Pogonyshev.                                #
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


# TODO: Merge this file into `notify/base.py' file when Py-notify relies on Python 2.5 or
#       later.  Also use __get_changed_signal() once functions end in the proper class.
#       Don't forget to remove various weirdness here meant to make Epydoc work smoothly
#       with module injection.



"""
Internal module used to implement Python 2.5 feautures of C{L{AbstractValueObject}} class.
I{Don’t import} this module directly: it is implementation detail and will be removed
eventually.
"""

__docformat__ = 'epytext en'
__all__       = ('storing', 'storing_safely', 'synchronizing', 'synchronizing_safely')



def storing (self, handler, *arguments):
    """
    Create a context manager that will temporarily store object value using C{handler}
    with C{arguments}.  Upon exit, returned context manager disconnects the handler from
    ‘changed’ signal, cancelling effect of C{L{store
    <notify.base.AbstractValueObject.store>}}.

    It is legal to modify handler list of ‘changed’ signal inside a C{with} block.  In
    particular, you can disconnect the handler yourself, before the context manager does
    so.  Remember, however, that the context manager will still try to disconnect, so this
    will give two disconnection of the handler.  If it is connected more than once, both
    disconnections will succeed.

    Example usage:
       >>> variable = Variable (1)
       ...
       ... def note (argument):
       ...     print argument
       ...
       ... variable.value = 2
       ... with variable.storing (note):
       ...     variable.value = 3
       ...
       ... variable.value = 4

    This code prints number 2 and 3, but not 1 or 4.  Number 2 is printed because
    C{store()} passes it as initializing value to C{note()} handler; 3 because C{note()}
    is connected to ‘changed’ signal at that time.  But by the time 4 is assigned to
    variable value, C{note()} is already disconnected.

    @note:
    This method is available only in Python 2.5 or newer.

    @note:
    To enable C{with} statement in Python 2.5 you need to add this line at the top of your
    module:
        >>> from __future__ import with_statement

    @param  handler:   the object to temporarily store value with.
    @type   handler:   callable

    @param  arguments: optional arguments prepended to the current value when invoking
                       C{handler}.

    @raises TypeError: if C{handler} is not callable or cannot be called with
                       C{arguments} and current object value.

    @see:  C{L{store <notify.base.AbstractValueObject.store>}}
    @see:  C{L{AbstractSignal.disconnect <notify.signal.AbstractSignal.disconnect>}}
    """

    self.store (handler, *arguments)

    try:
        yield self
    finally:
        self.changed.disconnect (handler, *arguments)


def storing_safely (self, handler, *arguments):
    """
    Create a context manager that will temporarily store object value using C{handler}
    with C{arguments}, but only if it is not connected to ‘changed’ signal already.  Upon
    exit, returned context manager disconnects the handler from ‘changed’ signal,
    cancelling effect of C{L{store_safe <notify.base.AbstractValueObject.store_safe>}}.
    See C{L{storing <notify.base.AbstractValueObject.storing>}} for more information.

    @note:
    This method is available only in Python 2.5 or newer.

    @note:
    To enable C{with} statement in Python 2.5 you need to add this line at the top of your
    module:
        >>> from __future__ import with_statement

    @param  handler:   the object to temporarily store value with.
    @type   handler:   callable

    @param  arguments: optional arguments prepended to the current value when invoking
                       C{handler}.

    @raises TypeError: if C{handler} is not callable or cannot be called with
                       C{arguments} and current object value.

    @see:  C{L{store_safe <notify.base.AbstractValueObject.store_safe>}}
    @see:  C{L{AbstractSignal.disconnect <notify.signal.AbstractSignal.disconnect>}}
    """

    if self.store_safe (handler, *arguments):
        try:
            yield self
        finally:
            self.changed.disconnect (handler, *arguments)
    else:
        yield self


def synchronizing (self, value_object, mediator = None):
    """
    Create a context manager that will temporarily synchronize object to another
    C{value_object}, optionally using C{mediator}.  Upon exit, returned context manager
    desynchronizes the two objects.

    @note:
    This method is available only in Python 2.5 or newer.

    @note:
    To enable C{with} statement in Python 2.5 you need to add this line at the top of your
    module:
        >>> from __future__ import with_statement

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
    @raises ValueError:   if current value of C{value_object} is not suitable for C{self}.

    @see:  C{L{synchronize <notify.base.AbstractValueObject.synchronize>}}
    @see:  C{L{desynchronize <notify.base.AbstractValueObject.desynchronize>}}
    """

    self.synchronize (value_object, mediator)

    try:
        yield self
    finally:
        self.desynchronize (value_object, mediator)


def synchronizing_safely (self, value_object, mediator = None):
    """
    Like C{L{synchronizing <notify.base.AbstractValueObject.synchronizing>}}, but uses
    C{L{synchronize_safe <notify.base.AbstractValueObject.synchronize_safe>}} /
    C{L{desynchronize <notify.base.AbstractValueObject.desynchronize>}} method pair.  Only
    if C{synchronize_safe} returns C{True}, returned context manager will call
    C{desynchronize} upon exit.  See C{L{synchronizing
    <notify.base.AbstractValueObject.synchronizing>}} for more information.

    @note:
    This method is available only in Python 2.5 or newer.

    @note:
    To enable C{with} statement in Python 2.5 you need to add this line at the top of your
    module:
        >>> from __future__ import with_statement

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
    @raises ValueError:   if current value of C{value_object} is not suitable for C{self}.

    @see:  C{L{synchronize_safe <notify.base.AbstractValueObject.synchronize_safe>}}
    @see:  C{L{desynchronize <notify.base.AbstractValueObject.desynchronize>}}
    """

    if self.synchronize_safe (value_object, mediator):
        try:
            yield self
        finally:
            self.desynchronize (value_object, mediator)
    else:
        yield self



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
