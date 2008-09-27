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


# TODO: Merge this file into `notify/signal.py' test file when Py-notify relies on Python
#       2.5 or later.  Don't forget to remove various weirdness here meant to make Epydoc
#       work smoothly with module injection.


"""
Internal module used to implement Python 2.5 feautures of C{L{AbstractSignal}} class.
I{Don’t import} this module directly: it is implementation detail and will be removed
eventually.
"""

__docformat__ = 'epytext en'
__all__       = ('connecting', 'connecting_safely', 'blocking')


from contextlib import contextmanager



@contextmanager
def connecting (self, handler, *arguments, **keywords):
    """
    connecting(self, handler, *arguments)

    Create a context manager temporarily connecting C{handler} with C{arguments} to the
    signal.  Upon exit, returned context manager disconnects the handler.

    It is legal to modify handler list of the signal inside a C{with} block.  In
    particular, you can disconnect the handler yourself, before the context manager does
    so.  Remember, however, that the context manager will still try to disconnect, so this
    will give two disconnection of the handler.  If it is connected more than once, both
    disconnections will succeed.

    Example usage:
       >>> def note (argument):
       ...     print argument
       ...
       ... with signal.connecting (note):
       ...     signal ('this is going to be noted')
       ...
       ... signal ('and this is not')

    @note:
    This method is available only in Python 2.5 or newer.

    @note:
    To enable C{with} statement in Python 2.5 you need to add this line at the top of your
    module:
        >>> from __future__ import with_statement

    @see:  C{L{connect}}
    @see:  C{L{disconnect}}
    """

    self.connect (handler, *arguments, **keywords)

    try:
        yield self
    finally:
        self.disconnect (handler, *arguments, **keywords)


@contextmanager
def connecting_safely (self, handler, *arguments, **keywords):
    """
    connecting_safely(self, handler, *arguments)

    Create a context manager temporarily connecting C{handler} with C{arguments} to the
    signal, but only if it is not connected already.  Only if the handler is connected,
    returned context manager will disconnect it again upon exit.  See C{L{connecting}} for
    details.

    @note:
    This method is available only in Python 2.5 or newer.

    @note:
    To enable C{with} statement in Python 2.5 you need to add this line at the top of your
    module:
        >>> from __future__ import with_statement

    @see:  C{L{connect_safe}}
    @see:  C{L{disconnect}}
    """

    if self.connect_safe (handler, *arguments, **keywords):
        try:
            yield self
        finally:
            self.disconnect (handler, *arguments, **keywords)
    else:
        yield self


@contextmanager
def blocking (self, handler, *arguments, **keywords):
    """
    blocking(self, handler, *arguments, **keywords)

    Create a context manager temporarily blocking C{handler} with C{arguments}.  Upon
    exit, returned context manager unblocks the handler.

    If the handler is not connected when context is entered, the manager does nothing
    during both entering and exiting.  In other words, if you enter a context, and only
    then connect and manually block the handler, it will I{not} be unblocked by the
    manager.

    Example usage:
       >>> def note (argument):
       ...     print argument
       ...
       ... signal.connect (note)
       ... signal ('this is going to be noted')
       ...
       ... with signal.blocking (note):
       ...     signal ('and this is not')
       ...
       ... signal ('but this will be noted again')

    @note:
    This method is available only in Python 2.5 or newer.

    @note:
    To enable C{with} statement in Python 2.5 you need to add this line at the top of your
    module:
        >>> from __future__ import with_statement

    @see:  C{L{block}}
    @see:  C{L{unblock}}
    """

    if self.block (handler, *arguments, **keywords):
        try:
            yield self
        finally:
            self.unblock (handler, *arguments, **keywords)
    else:
        yield self



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
