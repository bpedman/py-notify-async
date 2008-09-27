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


from contextlib import contextmanager



@contextmanager
def storing (self, handler, *arguments, **keywords):
    """
    storing(self, handler, *arguments)

    Create a context manager that will temporarily store object value using C{handler}
    with C{arguments}.  Upon exit, returned context manager disconnects the handler from
    ‘changed’ signal, cancelling effect of C{L{store}}.

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

    @see:  C{L{store}}
    @see:  C{L{AbstractSignal.disconnect}}
    """

    self.store (handler, *arguments, **keywords)

    try:
        yield self
    finally:
        self.changed.disconnect (handler, *arguments, **keywords)


@contextmanager
def storing_safely (self, handler, *arguments, **keywords):
    """
    storing_safely(self, handler, *arguments)

    Create a context manager that will temporarily store object value using C{handler}
    with C{arguments}, but only if it is not connected to ‘changed’ signal already.  Upon
    exit, returned context manager disconnects the handler from ‘changed’ signal,
    cancelling effect of C{L{store_safe}}.  See C{L{storing}} for more information.

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

    @see:  C{L{store_safe}}
    @see:  C{L{AbstractSignal.disconnect}}
    """

    if self.store_safe (handler, *arguments, **keywords):
        try:
            yield self
        finally:
            self.changed.disconnect (handler, *arguments, **keywords)
    else:
        yield self


@contextmanager
def synchronizing (self, value_object, mediator = None):
    """
    synchronizing(self, value_object, mediator=None)

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
                          C{L{AbstractMediator}}.
    @raises ValueError:   if C{self} and C{value_object} are the same object.
    @raises ValueError:   if either C{self} or C{value_object} is not mutable.
    @raises ValueError:   if current value of C{value_object} is not suitable for C{self}.

    @see:  C{L{synchronize}}
    @see:  C{L{desynchronize}}
    """

    self.synchronize (value_object, mediator)

    try:
        yield self
    finally:
        self.desynchronize (value_object, mediator)


@contextmanager
def synchronizing_safely (self, value_object, mediator = None):
    """
    synchronizing_safely(self, value_object, mediator=None)

    Like C{L{synchronizing}}, but uses C{L{synchronize_safe}} / C{L{desynchronize}} method
    pair.  Only if C{synchronize_safe} returns C{True}, returned context manager will call
    C{desynchronize} upon exit.  See C{L{synchronizing}} for more information.

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
                          C{L{AbstractMediator}}.
    @raises ValueError:   if C{self} and C{value_object} are the same object.
    @raises ValueError:   if either C{self} or C{value_object} is not mutable.
    @raises ValueError:   if current value of C{value_object} is not suitable for C{self}.

    @see:  C{L{synchronize_safe}}
    @see:  C{L{desynchronize}}
    """

    if self.synchronize_safe (value_object, mediator):
        try:
            yield self
        finally:
            self.desynchronize (value_object, mediator)
    else:
        yield self


@contextmanager
def changes_frozen (self):
    """
    changes_frozen(self)

    Create a context manager that will temporarily disable all emissions of ‘changed’
    signal for this object.  However, if object value changes while the context manager is
    in effect, it will emit ‘changed’ signal once, upon exiting.

    Returned context managers can be nested.  In this case, any nested freezing manager
    will I{not} emit ‘changed’ signal, leaving it for the outmost one.

    This method is useful in the following cases:

      - you expect many changes in object’s value, but want interested parties be informed
        about final result only, not about all intermediate states;

      - you expect at least two changes and the final result may be “no changes” compared
        to original;

      - you expect many changes, don’t care about intermediate states and want to improve
        performance.

    In the second case, if the result is indeed “no changes”, context manager ensures that
    ‘changed’ signal is not emitted at all.

    Example usage:
       >>> variable = Variable ()
       ... variable.changed.connect (lambda value: sys.stdout.write ('%s\\n' % value))
       ...
       ... with variable.changes_frozen ():
       ...     a_method_that_can_modify_value (variable)
       ...     another_similar_method (variable)

    @note:
    This method is available only in Python 2.5 or newer.

    @note:
    To enable C{with} statement in Python 2.5 you need to add this line at the top of your
    module:
        >>> from __future__ import with_statement
    """

    # Note: keep in sync with with_changes_frozen() in `notify/base.py'.

    if self._AbstractValueObject__flags >= 0:
        original_value                    = self.get ()
        self._AbstractValueObject__flags -= 4

        try:
            yield original_value
        finally:
            self._AbstractValueObject__flags += 4
            new_value                         = self.get ()

            if new_value != original_value:
                self._value_changed (new_value)
    else:
        yield



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
