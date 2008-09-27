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
L{Signals <AbstractSignal>} are lists of callables (I{handlers}) that are called in turn
when the signal is I{emitted}.  They allow for separation between initiators and listeners
of some event.

Here is an unrealistic example of usage:

    >>> from notify.signal import *
    ... import sys
    ...
    ... night = Signal ()
    ... night.connect (lambda: sys.stdout.write ("It's late already\\n"))
    ...
    ... class Person (object):
    ...     def __init__(self, name, is_active = False):
    ...         self.__name      = name
    ...         self.__is_active = is_active
    ...         night.connect (self.__on_night)
    ...     def go_on_a_trip (self):
    ...         sys.stdout.write ('%s goes on a trip\\n' % self.__name)
    ...         night.disconnect (self.__on_night)
    ...     def __on_night (self):
    ...         if self.__is_active:
    ...             sys.stdout.write ('%s goes to a dancing\\n' % self.__name)
    ...         else:
    ...             sys.stdout.write ('%s yawns and goes to sleep\\n' % self.__name)
    ...
    ... bob   = Person ('Bob')
    ... irene = Person ('Irene')
    ... pete  = Person ('Pete', True)
    ...
    ... night.emit ()
    ... irene.go_on_a_trip ()
    ... night.emit ()

It gives the following output::

    It's late already
    Bob yawns and goes to sleep
    Irene yawns and goes to sleep
    Pete goes to a dancing
    Irene goes on a trip
    It's late already
    Bob yawns and goes to sleep
    Pete goes to a dancing

Note that the program itself only decides “when a night starts”, it doesn’t know what
happens to whom then.  Class C{Person} connects or disconnects its handler to C{night}
signal itself.

Brief Comparison With GObject Signals
=====================================

    U{PyGObject <http://pygtk.org/>} provides its own kind of signals.  They may or may
    not be more efficient for your particular case and which implementation to use is of
    course your choice.  Here is a brief list of major differences.

      - Py-notify signals are objects.  Therefore, they are not bound to class contexts
        and can be passed around, created locally and so on.

      - There is no default handler for a class in Py-notify.  Since signals are not bound
        to classes, this is even impossible.

      - Py-notify signal handlers are not type-safe.  This is a result of native Pythonic
        implementation.  (PyGObject wraps C signals from U{GLib <http://gtk.org/>}.)

      - There are no connection IDs, handlers can be disconnected only by passing the same
        handler to C{L{disconnect <AbstractSignal.disconnect>}} method.  This is less
        efficient, but easier to use.

      - Py-notify signals are U{slower <http://home.gna.org/py-notify/benchmark.html>}.
        This may be important in time-critical code if you use signals heavily.

    In general, you should use whatever suits your needs better.  GObject signals are
    limited to C{gobject.GObject} class derivatives.

G{classtree AbstractSignal}
"""

__docformat__ = 'epytext en'
__all__       = ('AbstractSignal', 'Signal', 'CleanSignal')


import sys
import weakref

from notify.bind  import Binding, WeakBinding
from notify.gc    import AbstractGCProtector
from notify.utils import is_callable, raise_not_implemented_exception

try:
    import contextlib
except ImportError:
    # Ignore, related features will not be provided.
    pass



#-- Signal interface classes -----------------------------------------

class AbstractSignal (object):

    """
    Abstract interface all signal classes must implement.

    @group Connecting Handlers:
    is_connected, connect, connect_safe, do_connect, do_connect_safe, disconnect,
    disconnect_all, connecting, connecting_safely

    @group Blocking Handlers:
    is_blocked, block, unblock, blocking

    @group Emission:
    __call__, emit, stop_emission, emission_level, emission_stopped

    @group Handler List Maintenance:
    has_handlers, __nonzero__, count_handlers, collect_garbage

    @group Methods for Subclasses:
    _wrap_handler, _additional_description

    @group Internals:
    _get_emission_level, _is_emission_stopped, __to_string

    @sort:
    is_connected, connect, connect_safe, do_connect, do_connect_safe, disconnect,
    disconnect_all, connecting, connecting_safely,
    is_blocked, block, unblock, blocking,
    __call__, emit, stop_emission, emission_level, emission_stopped,
    has_handlers, __nonzero__, count_handlers, collect_garbage,
    _wrap_handler, _additional_description
    """

    __slots__ = ()


    class AbstractAccumulator (object):

        """
        An accumulator of signal handlers results.  It may combine, alter or discard
        values, post-process values after all handlers run (or emission stops for some
        reason) or stop emission based on the values.

        Note that accumulator must I{not} contain the accumulated value or have any
        internal state (except that specified by C{__init__} arguments) whatsoever.  This
        no-OOP design is required to make accumulators thread- and reentrance-safe, so
        that the same accumulator can be used from multiple threads or nested signal
        emissions.  Any state must be stored in external variable C{accumulated_value},
        which is passed to all appropriate functions.
        """

        __slots__ = ()


        def get_initial_value (self):
            """
            Get initial value for this accumulator.  This value will be passed to the
            first invocation of C{L{accumulate_value}} method.  Default implementation
            returns C{None}.

            @rtype: C{object}
            """

            return None

        def accumulate_value (self, accumulated_value, value_to_add):
            """
            Accumulate C{value_to_add} into C{accumulated_value} and return the result.
            Result will be passed to next invocation of this method, if any.

            @param accumulated_value: value, returned from the last call to
                                      C{accumulated_value} or C{L{get_initial_value}}.
            @param value_to_add:      next handler value, to be added to
                                      C{accumulated_value}.

            @rtype:                   C{object}
            @returns:                 New accumulated value, combination of
                                      C{accumulated_value} and C{value_to_add}.
            """

            raise_not_implemented_exception (self)

        def should_continue (self, accumulated_value):
            """
            Examine C{accumulated_value} and decide if signal emission should continue.
            Default implementation always returns C{True}.

            @param accumulated_value: value, returned from the last call to
                                      C{accumulated_value}.

            @rtype:                   C{bool}
            @returns:                 Whether signal emission should continue.
            """

            return True

        def post_process_value (self, accumulated_value):
            """
            Post-process C{accumulated_value} and return new value.  This method is called
            after signal emission ends, either because there are no more handlers or it
            was stopped by C{L{should_continue}} or from outside, using
            C{L{AbstractSignal.stop_emission}} method.  Default implementation does
            nothing and returns C{accumulated_value} unchanged.

            @param accumulated_value: value, returned from the last call to
                                      C{accumulated_value} or C{L{get_initial_value}}.

            @rtype:                   C{object}
            @returns:                 Final accumulated value, either C{accumulated_value}
                                      or some transformation of it.
            """

            return accumulated_value


    class AnyAcceptsAccumulator (AbstractAccumulator):

        """
        An accumulator that stops emission if any handler returns a non-zero value and
        sets emission result to it in this case.  If all handlers return zero values,
        signal emission is not stopped and result is returned by last handler.  If there
        are no handlers at all, emission result is C{False}.

        @note: Whether a value is non-zero is determined as by built-in C{bool} function.
        """

        __slots__ = ()


        def get_initial_value (self):
            return False

        def accumulate_value (self, accumulated_value, value_to_add):
            return value_to_add

        def should_continue (self, accumulated_value):
            return not accumulated_value


    class AllAcceptAccumulator (AbstractAccumulator):

        """
        An accumulator that stops emission if any handler returns a zero value and sets
        emission result to it in this case.  If all handlers return non-zero values,
        signal emission is not stopped and result is returned by last handler.  If there
        are no handlers at all, emission result is C{True}.

        @note: Whether a value is non-zero is determined as by built-in C{bool} function.
        """

        __slots__ = ()


        def get_initial_value (self):
            return True

        def accumulate_value (self, accumulated_value, value_to_add):
            return value_to_add

        def should_continue (self, accumulated_value):
            return accumulated_value


    class LastValueAccumulator (AbstractAccumulator):

        """
        An accumulator that always returns the value returned by last handler.  If there
        are no handlers at all, emission result is C{None}.
        """

        __slots__ = ()


        def accumulate_value (self, accumulated_value, value_to_add):
            return value_to_add


    class ValueListAccumulator (AbstractAccumulator):

        """
        An accumulator that returns a list of all handler results.  If there are no
        handlers at all, emission result is an empty list.
        """

        __slots__ = ()


        def get_initial_value (self):
            return []

        def accumulate_value (self, accumulated_value, value_to_add):
            accumulated_value.append (value_to_add)
            return accumulated_value


    ANY_ACCEPTS = AnyAcceptsAccumulator ()
    "An instance of C{L{AnyAcceptsAccumulator}}."

    ALL_ACCEPT = AllAcceptAccumulator ()
    "An instance of C{L{AllAcceptAccumulator}}."

    LAST_VALUE = LastValueAccumulator ()
    "An instance of C{L{LastValueAccumulator}}."

    VALUE_LIST = ValueListAccumulator ()
    "An instance of C{L{ValueListAccumulator}}."


    def has_handlers (self):
        """
        Determine if the signal has any handlers or if it is not known.  Note that return
        value of C{True} indicates that there I{might} be handlers.  Return value of
        C{False} indicates that is there is I{certainly no} handlers.

        This method can be used to find if computing emission arguments can be skipped
        completely: if no one is listening, why emit at all?  This can be handy if
        computing emission arguments is not cheap.

        @rtype:   C{bool}
        @returns: C{True} if there are handlers or if there I{might} be handlers.
        """

        raise_not_implemented_exception (self)

    def __nonzero__(self):
        """
        Same as C{L{has_handlers}} method.

        @rtype:   C{bool}
        @returns: C{True} if there are handlers or if there I{might} be handlers.
        """

        return self.has_handlers ()

    if sys.version_info[0] >= 3:
        __bool__ = __nonzero__
        del __nonzero__


    def count_handlers (self):
        """
        Get the full number of handlers connected to this signal.  This method might be
        (comparatively) slow.  Unless you really need an exact number, consider using
        C{L{has_handlers}} instead.  This method is called by package implementation only
        when creating string representation of a signal or L{value
        <base.AbstractValueObject>} based on it.

        @rtype:   C{int}
        @returns: Total number of connected handlers.
        """

        raise_not_implemented_exception (self)


    def is_connected (self, handler, *arguments, **keywords):
        """
        Determine if C{handler} with C{arguments} is connected to the signal.  Note that
        this method doesn’t detect if there are several handlers equal to C{handler}
        connected.

        @rtype: C{bool}
        """

        raise_not_implemented_exception (self)

    def is_blocked (self, handler, *arguments, **keywords):
        """
        Determine if C{handler} with C{arguments} is connected to the signal and blocked.
        Note that if there are several handlers equal to C{handler} connected, all are
        either blocked or non-blocked.

        @rtype: C{bool}
        """

        raise_not_implemented_exception (self)


    def connect (self, handler, *arguments, **keywords):
        """
        Connect C{handler} with C{arguments} to the signal.  This means that upon signal
        emission the handler will be called with emission arguments I{appended} to the
        connection-time C{arguments} (of couse, either or both of the tuples can be
        empty.)  The handler can be later L{disconnected <disconnect>} if needed.  A
        connected handler can also be L{blocked <block>} and later L{unblocked <unblock>}.
        Note that it is legal to connect the same handler and with the same arguments
        several times and the handler will be called that many times on signal emission.

        All standard implementations of C{AbstractSignal} interface will automatically
        disconnect method handlers of garbage-collected objects.  For details, please see
        C{L{WeakBinding}} class documentation.

        @note:
        Descendant classes don’t normally need to override this method.  Override
        C{L{do_connect}} and/or C{L{_wrap_handler}} instead.
        """

        self.do_connect (self._wrap_handler (handler, *arguments, **keywords))

    def connect_safe (self, handler, *arguments, **keywords):
        """
        Connect C{handler} with C{arguments} to the signal unless it is connected already.
        This method either behaves identically to C{L{connect}} (if the handler is not
        connected yet), or does nothing.  See documentation of C{L{connect}} method for
        details.

        @rtype:   C{bool}
        @returns: C{True} if it has connected C{handler} with C{arguments}, C{False} if it
                  had been connected already.
        """

        if not self.is_connected (handler, *arguments, **keywords):
            self.do_connect (self._wrap_handler (handler, *arguments, **keywords))
            return True
        else:
            return False


    def _wrap_handler (self, handler, *arguments, **keywords):
        """
        Wrap C{handler} with C{arguments} into a single internally-used object.  It is
        legal to return C{handler} itself if C{arguments} tuple is empty and the class
        doesn’t need any special behaviour from the returned object.

        Normally, this method should call C{L{Binding.wrap}} or a similar method (e.g. of
        a subclass.)  In any case, returned object I{must} compare equal to
        C{Binding (handler, arguments)}.

        This method I{must not} be called from outside.

        @rtype: C{object}
        """

        return WeakBinding.wrap (handler, arguments, None, keywords)


    def do_connect (self, handler):
        """
        Connect C{handler} to the signal without any further modifications.  See
        C{L{connect}} method for details.

        This method I{may} be called from outside, but most of the time you should use
        C{L{connect}} instead.  Note that since signal class will not do any handler
        modification at this point, calling C{do_connect} directly I{may break} promises
        of the signal class.
        """

        raise_not_implemented_exception (self)

    def do_connect_safe (self, handler):
        """
        Connect C{handler} to the signal unless it is connected already, without any
        further modifications.  See C{L{connect}} method for details.

        This method I{may} be called from outside, but most of the time you should use
        C{L{connect_safe}} instead.  Note that since signal class will not do any handler
        modification at this point, calling C{do_connect} directly I{may break} promises
        of the signal class.

        @rtype:   C{bool}
        @returns: C{True} if it has connected C{handler}, C{False} if it had been
                  connected already.
        """

        if not self.is_connected (handler):
            self.do_connect (handler)
            return True
        else:
            return False


    def disconnect (self, handler, *arguments, **keywords):
        """
        Disconnect C{handler} with C{arguments} from the signal.  This means that upon
        signal emission the handler will not be called anymore.  Note that it is legal to
        connect the same handler and with the same arguments several times and this method
        only cancels one connection.  If you need to remove all connected instances of the
        C{handler}, use C{L{disconnect_all}}.

        All standard implementations of C{AbstractSignal} interface will automatically
        disconnect method handlers of garbage-collected objects.  Therefore, you don’t
        need to call this method if the object is ‘thrown away’ already and handlers are
        ‘harmless’.  For details, please see C{L{WeakBinding}} class documentation.

        @rtype:   C{bool}
        @returns: C{True} if C{handler} has been disconnected; C{False} if it was not even
                  connected or had more than one connection.
        """

        raise_not_implemented_exception (self)


    def disconnect_all (self, handler, *arguments, **keywords):
        """
        Disconnect all instances of C{handler} with C{arguments} from the signal.  This
        means that upon signal emission the handler will not be called anymore.  Note that
        it is legal to connect the same handler and with the same arguments several times
        and this method cancels I{all} such connection.

        All standard implementations of C{AbstractSignal} interface will automatically
        disconnect method handlers of garbage-collected objects.  Therefore, you don’t
        need to call this method if the object is ‘thrown away’ already and handlers are
        ‘harmless’.  For details, please see C{L{WeakBinding}} class documentation.

        @rtype:   C{bool}
        @returns: C{True} if C{handler} has been disconnected; C{False} if it was not even
                  connected to begin with.
        """

        if self.disconnect (handler, *arguments, **keywords):
            while self.disconnect (handler, *arguments, **keywords):
                pass

            return True

        else:
            return False


    def block (self, handler, *arguments, **keywords):
        """
        Block C{handler} with C{arguments} from being called during subsequent emissions.
        If C{handler} is not connected to the signal to begin with, do nothing and return
        C{False}.  Else return C{True}.  Note that since it is impossible to distinguish
        between equal handlers, if there are several handlers equal to C{handler} with
        C{arguments} connected, all get blocked.

        Blocked handlers can be later unblocked.  You need to call C{L{unblock}} exactly
        the same number of times as this method for a handler to be considered
        non-blocked.  This is usually what you want.

        @rtype:   C{bool}
        @returns: C{True} if C{handler} has been blocked, C{False} if it is not connected
                  to begin with.
        """

        raise_not_implemented_exception (self)

    def unblock (self, handler, *arguments, **keywords):
        """
        Unblock a C{handler} with C{arguments}.  If the C{handler} is not connected or is
        not blocked, do nothing and return C{False}.  Else decrement its ‘block counter’
        and return C{True} only if it becomes non-blocked as a result.  Note that handlers
        must be unblocked exactly the same number of times as blocked, to become
        non-blocked again.

        @rtype:   C{bool}
        @returns: C{True} if C{handler} becomes non-blocked; C{False} if it is not even
                  connected or still remains blocked.
        """

        raise_not_implemented_exception (self)


    if 'contextlib' in globals ():
        # This is a collection of gross hacks aimed at making this work (obviously) _and_
        # tricking Epydoc into not noticing that we import stuff from a different module.

        from notify._2_5 import signal as _2_5

        connecting                   = _2_5.connecting
        connecting_safely            = _2_5.connecting_safely
        blocking                     = _2_5.blocking

        # This is needed so that Epydoc sees docstrings as UTF-8 encoded.
        connecting.__module__        = __module__
        connecting_safely.__module__ = __module__
        blocking.__module__          = __module__

        del _2_5


    def emit (self, *arguments, **keywords):
        """
        Invoke non-blocked handlers connected to C{self}, passing C{arguments} to them.
        Whether all handlers are called and the return value of this method are determined
        by semantics of derived class.  Normally, they are influenced by L{accumulator
        <AbstractAccumulator>} (if any) with which the signal was created.  Custom
        subclasses may supply different semantics.

        Note that if a given handler was connected to this signal with any arguments,
        C{arguments} to this method are I{appended} to those specified at connection time.

        @rtype:   C{object}
        @returns: Value, determined by subclass and, possibly, by its
                  L{accumulator <AbstractAccumulator>}.
        """

        raise_not_implemented_exception (self)

    def __call__(self, *arguments, **keywords):
        """
        Same as C{L{emit}} method.

        @note:
        Don’t override this method, override C{emit} instead, if really needed.

        @rtype:   C{object}
        @returns: Value, determined by subclass and, possibly, by its
                  L{accumulator <AbstractAccumulator>}.
        """
        return self.emit (*arguments, **keywords)


    def _get_emission_level (self):
        """
        Internal getter for the C{L{emission_level}} property.  Outside code should use
        that property, not the method directly.

        @rtype: C{int}
        """

        raise_not_implemented_exception (self)

    def _is_emission_stopped (self):
        """
        Internal getter for the C{L{emission_stopped}} property.  Outside code should use
        that property, not the method directly.

        @rtype: C{bool}
        """

        raise_not_implemented_exception (self)

    def stop_emission (self):
        """
        Stop the current emission of the signal.  If there is no emission in progress to
        begin with or if the current emission is already stopped with a call to this
        method, do nothing and return C{False}, else return C{True}.  This method only
        stops the latest emission, earlier ones proceed normally (this is relevant only to
        recursive emissions.)

        Note that it is legal to stop the current emission and immediately start a new
        one, without letting the previous call to C{L{emit}} return first.  One possible
        use is to make the first handler check the emission arguments and, if needed,
        ‘correct’ them, stop emission and immediately reemit signal with new, fixed
        arguments.

        @rtype:   C{bool}
        @returns: C{True} if this method stopped anything.
        """

        raise_not_implemented_exception (self)


    def collect_garbage (self):
        """
        Make the signal disconnect all handlers of garbage-collected objects.  Signal is
        not required to do anything, this method is merely a ‘request’ to remove garbage.
        For instance, C{L{Signal}} will remove garbage only when not emitting.

        You rarely need to call this method explicitely, since standard signals call it
        after any emission themselves.  For C{L{CleanSignal}} it doesn’t make sense at
        all, since those signals will remove such handlers automatically.
        """

        pass


    emission_level   = property (lambda self: self._get_emission_level (),
                                 doc = ("""
                                 The number of unfinished calls to C{L{emit}} method of
                                 this signal.  For instance, if this signal hasn’t been
                                 emitted at all, the return value will be 0.  If called
                                 from a handler, return value will be at least 1—more if
                                 in recursive emission.

                                 Note that stopping an emission doesn’t cause emission
                                 level to change instantly.  Even though the latest
                                 emission will not invoke handlers anymore, it is still
                                 considered ‘in progress’ until the call to C{L{emit}}
                                 returns.

                                 @type: int
                                 """))

    emission_stopped = property (lambda self: self._is_emission_stopped (),
                                 doc = ("""
                                 Flag indicating if the latest emission in progress has
                                 been stopped with C{L{stop_emission}} method.  In
                                 particular, it is C{False} if (but not only if) the
                                 signal is not being emitted at all.

                                 Note that this property only considers I{the latest}
                                 emission.  For instance, immediately after a call to
                                 C{stop_emission} it is C{True}, but if you start another
                                 one—letting or not the stopped to finish—it will become
                                 C{False}.  In other words, C{False} doesn’t mean there is
                                 no stopped emission in progress, it only means that the
                                 latest emission is not stopped, or the signal is not
                                 being emitted at all.

                                 @type: bool
                                 """))


    if sys.version_info[:3] >= (2, 5):
        def default_exception_handler (signal, exception, handler):
            if not isinstance (exception, Exception):
                raise exception
            else:
                sys.excepthook (*sys.exc_info ())

    else:
        def default_exception_handler (signal, exception, handler):
            if isinstance (exception, (SystemExit, KeyboardInterrupt)):
                raise exception
            else:
                sys.excepthook (*sys.exc_info ())


    default_exception_handler.__doc__ = \
    ("""
     Default handler for exceptions occured in signal handlers.  If C{exception} is not
     C{SystemExit} or C{KeyboardInterrupt}, it is printed to C{sys.stderr} or, more
     exactly, passed to C{sys.excepthook}.  Otherwise it is reraised and so thrown out of
     signal emission.  This is most often what you want: errors in handlers won’t break
     unsuspecting signal emissions, while non-errors (C{SystemExit} and
     C{KeyboardInterrupt}) will be propagated further.

     On Python 2.5 C{default_exception_handler} is defined a little differently.
     Specifically, instances of C{Exception} class will be passed to C{sys.excepthook} and
     all other exceptions will be reraised.  For standard exceptions this is exactly the
     same as described above.  There may be differences for custom exception types only,
     but then you probably derived from C{BaseException} specifically for exception not to
     be caught by default.

     @see:  exception_handler
     """)


    def ignoring_exception_handler (signal, exception, handler):
        """
        Handler for exceptions occured in signal handlers that ignores all exceptions.
        This handler is just a simple C{pass}.  It ignores everything, including
        C{SystemExit} and C{KeyboardInterrupt}.

        @param signal:    signal, in which emission an exception was raised.
        @type  signal:    C{AbstractSignal}

        @param exception: raised exception object (same as C{sys.exc_info () [1]}.)

        @param handler:   signal handler that rose the exception.
        @type  handler:   callable

        @see:  exception_handler
        """

        pass


    def printing_exception_handler (signal, exception, handler):
        """
        Handler for exceptions occured in signal handlers that passes all exceptions to
        C{sys.excepthook}.  Otherwise, exceptions are ignored and never reraised (except
        if reraised by C{sys.excepthook} itself.)

        @param signal:    signal, in which emission an exception was raised.
        @type  signal:    C{AbstractSignal}

        @param exception: raised exception object (same as C{sys.exc_info () [1]}.)

        @param handler:   signal handler that rose the exception.
        @type  handler:   callable

        @see:  exception_handler
        """

        sys.excepthook (*sys.exc_info ())


    def reraising_exception_handler (signal, exception, handler):
        """
        Handler for exceptions occured in signal handlers that reraises all exceptions.
        Regardless of exception type it is always thrown out of the emission call.

        @param signal:    signal, in which emission an exception was raised.
        @type  signal:    C{AbstractSignal}

        @param exception: raised exception object (same as C{sys.exc_info () [1]}.)

        @param handler:   signal handler that rose the exception.
        @type  handler:   callable

        @see:  exception_handler
        """

        raise exception


    default_exception_handler   = staticmethod (default_exception_handler)
    ignoring_exception_handler  = staticmethod (ignoring_exception_handler)
    printing_exception_handler  = staticmethod (printing_exception_handler)
    reraising_exception_handler = staticmethod (reraising_exception_handler)


    exception_handler           = default_exception_handler
    """
    Handler for exceptions occured in signal handlers.  When a signal handler doesn’t
    return but raises an exception instead, C{AbstractSignal.exception_handler} is called.
    It can be any function accepting three arguments: signal, exception and handler (in
    that order.)  In addition, exception handler can use information in C{sys.exc_info},
    if needed.

    If exception handler returns, emission continues as normal and any returned value is
    discarded.  However, if it raises any exception (e.g., it may reraise exception for
    which it is called), the exception will be thrown out of the corresponding call to
    C{L{emit}}.

    Default value is C{L{default_exception_handler}}.  This method can be assigned any
    appropriate value.
    """


    def _additional_description (self, formatter):
        """
        Generate list of additional descriptions for this object.  All description strings
        are put in parentheses after basic signal description and are separated by
        semicolons.  Default description mentions number of handlers if there are any at
        all.

        C{formatter} is either C{repr} or C{str} and should be used to format objects
        mentioned in list string(s).  Its use is not required but encouraged.

        Overriden method should look like this:

            >>> def _additional_description (self, formatter):
            ...     return (['my-description']
            ...             + super (..., self)._additional_description (formatter))

        You may selectively remove descriptions generated by superclasses, but remember
        that some of them (including this class) may generate varying number of
        descriptions, so this may be not trivial to do.  In general, there are no
        requirements on contents of returned list, except that it must contain only
        strings.

        This method is called by standard implementations of C{L{__repr__}} and
        C{L{__str__}}.  If you use your own (and that is perfectly fine), you don’t need
        to override this method.

        @param formatter: function (either C{repr} or C{str}) that can be used to format
                          various objects.

        @rtype:           C{list}
        @returns:         List of description strings for this object.
        """

        try:
            num_handlers = self.count_handlers ()

            if num_handlers > 1:
                return ['%d handlers' % num_handlers]
            elif num_handlers == 1:
                return ['1 handler']

        except NotImplementedError:
            return 'count_handlers() not implemented'

        return []

    def __to_string (self, strict):
        if strict:
            additional_description = self._additional_description (repr)
        else:
            additional_description = self._additional_description (str)

        if additional_description:
            return ' (%s)' % '; '.join (additional_description)
        else:
            return ''


    def __repr__(self):
        # It is impossible to recreate signal, so don't try to generate a valid Python
        # expression.
        return ('<%s.%s at 0x%x%s>'
                % (self.__module__, self.__class__.__name__, id (self), self.__to_string (True)))


    def __str__(self):
        return '<%s at 0x%x%s>' % (self.__class__.__name__, id (self), self.__to_string (True))



#-- Standard signal classes ------------------------------------------

class Signal (AbstractSignal):

    """
    Standard implementation of C{L{AbstractSignal}} interface.

    Signal can have an L{accumulator <AbstractAccumulator>} for values, returned by its
    handlers.  By default, these values are just ignored.

    Note that standard signals cannot be weakly referenced.  For standard signals weak
    references don’t make much sense anyway.  If you need them, you are probably
    interested in C{L{CleanSignal}}.
    """

    __slots__ = ('_handlers', '_blocked_handlers', '__accumulator', '__emission_level')


    def __init__(self, accumulator = None):
        """
        Create a new C{Signal} with specified C{accumulator}.  By default, the signal will
        not have any accumulator, so its C{L{emit}} method will always discard handlers’s
        return values and return C{None}.

        @param  accumulator: optional accumulator for signal handlers’ return values.
        @type   accumulator: C{L{AbstractAccumulator}} or C{None}

        @raises TypeError:   if C{accumulator} is not C{None} and not an instance of
                             C{AbstractAccumulator}.
        """

        if not (accumulator is None or isinstance (accumulator, Signal.AbstractAccumulator)):
            raise TypeError ("you must provide a 'Signal.AbstractAccumulator' or None")

        super (Signal, self).__init__()

        self._handlers         = None
        self._blocked_handlers = _EMPTY_TUPLE
        self.__accumulator     = accumulator
        self.__emission_level  = 0


    accumulator = property (lambda self: self.__accumulator,
                            doc = ("""
                            The L{accumulator <AbstractAccumulator>} this signal was
                            created with or C{None}.  Accumulator cannot be changed, it
                            can only be specified at signal creation time.

                            @type: AbstractAccumulator
                            """))


    def has_handlers (self):
        if self._handlers is None:
            return False

        for handler in self._handlers:
            if handler is not None and (not isinstance (handler, WeakBinding) or handler):
                return True

        return False

    def count_handlers (self):
        num_handlers = 0

        if self._handlers is not None:
            for handler in self._handlers:
                if handler is not None and (not isinstance (handler, WeakBinding) or handler):
                    num_handlers += 1

        return num_handlers


    def is_connected (self, handler, *arguments, **keywords):
        if self._handlers is not None and is_callable (handler):
            if arguments or keywords:
                handler = Binding (handler, arguments, keywords)

            return handler in self._handlers

        else:
            return False


    def is_blocked (self, handler, *arguments, **keywords):
        if self._blocked_handlers is not _EMPTY_TUPLE and is_callable (handler):
            if arguments or keywords:
                handler = Binding (handler, arguments, keywords)

            return handler in self._blocked_handlers

        else:
            return False


    def do_connect (self, handler):
        if self._handlers is not None:
            self._handlers.append (handler)
        else:
            self._handlers = [handler]


    # Implementation note: we set disconnected (or garbage-collected) handlers to None,
    # instead of removing them right away.  This is done to prevent spoiling
    # disconnections made when emission is in effect.


    def disconnect (self, handler, *arguments, **keywords):
        handlers = self._handlers
        if handlers is None or not is_callable (handler):
            return False

        if arguments or keywords:
            handler = Binding (handler, arguments, keywords)

        # Note: we must disconnect _last_ of equal connected handlers, in order to make
        # connect()/disconnect() a no-op.  We use a custom loop because of that (and since
        # reversed() only appeared in 2.4.)

        index = len (handlers) - 1
        while index >= 0:
            if handlers[index] != handler:
                index -= 1
            else:
                if self.__emission_level == 0:
                    del handlers[index]
                else:
                    handlers[index] = None

                if (    self._blocked_handlers is not _EMPTY_TUPLE
                    and handler not in handlers[:index]):
                    # This is the last handler, need to make sure it is not listed in
                    # `_blocked_handlers'.
                    self._blocked_handlers = [_handler for _handler in self._blocked_handlers
                                              if _handler != handler]

                    if not self._blocked_handlers:
                        self._blocked_handlers = _EMPTY_TUPLE

                if not handlers:
                    self._handlers = None

                return True

        return False


    # Overriden for efficiency.

    def disconnect_all (self, handler, *arguments, **keywords):
        if self._handlers is None or not is_callable (handler):
            return False

        if arguments or keywords:
            handler = Binding (handler, arguments, keywords)

        if self.__emission_level == 0:
            old_length     = len (self._handlers)
            self._handlers = [_handler for _handler in self._handlers if _handler != handler]
            any_removed    = (len (self._handlers) != old_length)

            if not self._handlers:
                self._handlers = None

        else:
            any_removed = False

            for index, _handler in enumerate (self._handlers):
                if _handler == handler:
                    self._handlers[index] = None
                    any_removed           = True

        if any_removed and self._blocked_handlers is not _EMPTY_TUPLE:
            self._blocked_handlers = [_handler for _handler in self._blocked_handlers
                                      if _handler != handler]

            if not self._blocked_handlers:
                self._blocked_handlers = _EMPTY_TUPLE

        return any_removed


    # Note: we rely on the way remove() works to fulfill our blocking obligations.


    def block (self, handler, *arguments, **keywords):
        if is_callable (handler) and self._handlers is not None:
            if arguments or keywords:
                handler = Binding (handler, arguments, keywords)

            if handler in self._handlers:
                if self._blocked_handlers is not _EMPTY_TUPLE:
                    self._blocked_handlers.append (handler)
                else:
                    self._blocked_handlers = [handler]

                return True

        return False


    def unblock (self, handler, *arguments, **keywords):
        if self._blocked_handlers is _EMPTY_TUPLE or not is_callable (handler):
            return False

        if arguments or keywords:
            handler = Binding (handler, arguments, keywords)

        try:
            self._blocked_handlers.remove (handler)

            if not self._blocked_handlers:
                self._blocked_handlers = _EMPTY_TUPLE

            return True

        except ValueError:
            # It is not blocked to begin with.
            return False


    def emit (self, *arguments, **keywords):
        # Speed optimization.
        handlers    = self._handlers
        accumulator = self.__accumulator

        if accumulator is not None:
            value = accumulator.get_initial_value ()

        if handlers is not None:
            try:
                saved_emission_level  = self.__emission_level
                self.__emission_level = abs (saved_emission_level) + 1
                might_have_garbage    = False

                for handler in handlers:
                    # Disconnected while in emission handlers are temporary set to None.
                    if handler is None:
                        might_have_garbage = True
                        continue

                    if self.__emission_level < 0:
                        might_have_garbage = True
                        break

                    # We need to refetch that blocked handlers list before processing each
                    # handler, because it may change during emission.
                    if handler in self._blocked_handlers:
                        continue

                    # This somewhat illogical transposition of terms is for speed
                    # optimization.  `not handler' must be side-effect free anyway, so it
                    # doesn't matter which term is evaluated first.
                    if not handler and isinstance (handler, WeakBinding):
                        # Handler will be removed in collect_garbage(), don't bother now.
                        might_have_garbage = True
                        continue

                    # Another speed optimization, check if we even need that
                    # `handler_value' first.
                    if accumulator is None:
                        try:
                            handler (*arguments, **keywords)
                        except:
                            AbstractSignal.exception_handler (self, sys.exc_info () [1], handler)
                    else:
                        try:
                            handler_value = handler (*arguments, **keywords)
                        except:
                            AbstractSignal.exception_handler (self, sys.exc_info () [1], handler)
                        else:
                            value = accumulator.accumulate_value (value, handler_value)
                            if not accumulator.should_continue (value):
                                might_have_garbage = True
                                break
            finally:
                self.__emission_level = saved_emission_level
                if might_have_garbage and saved_emission_level == 0:
                    self.collect_garbage ()

        if accumulator is None:
            return None
        else:
            return accumulator.post_process_value (value)


    def _get_emission_level (self):
        return abs (self.__emission_level)

    def _is_emission_stopped (self):
        return self.__emission_level < 0

    def stop_emission (self):
        # Check if we are in emission at all or if emission is not stopped already.
        if self.__emission_level > 0:
            self.__emission_level = -self.__emission_level
            return True
        else:
            return False


    def collect_garbage (self):
        # NOTE: If, for some reason, you change this, don't forget to adjust
        #       `CleanSignal.collect_garbage' accordingly.

        # Don't remove disconnected or garbage-collected handlers if in nested emission,
        # it will spoil emit() calls completely.
        if self._handlers is not None and self.__emission_level == 0:
            self._handlers = ([handler for handler in self._handlers
                               if handler is not None and (not isinstance (handler, WeakBinding)
                                                           or handler)]
                              or None)


    def _additional_description (self, formatter):
        if self.__accumulator is not None:
            descriptions = ['accumulator: %s' % formatter (self.__accumulator)]
        else:
            descriptions = []

        return descriptions + super (Signal, self)._additional_description (formatter)



#-- Handler auto-disconnecting signal class --------------------------

class CleanSignal (Signal):

    """
    Subclass of C{L{Signal}} which wraps its handlers in such a way that garbage-collected
    ones are detected instantly.  Clean signals also have a notion of I{parent}, which
    they L{prevent from being garbage-collected <notify.gc>}, but only if there is at
    least one handler.

    Also, unlike plain C{Signal}, C{CleanSignal} allows to weakly reference itself.
    """

    __slots__ = ('__parent', '__weakref__')


    def __init__(self, parent = None, accumulator = None):
        """
        Create a new C{CleanSignal} with specified C{parent} and C{accumulator}.  If
        C{parent} is not C{None}, it will be protected from garbage collection while the
        signal has at least one handler (initially it doesn’t.)

        @raises TypeError: if C{accumulator} is not C{None} and not an instance of
                           C{L{AbstractAccumulator}}.
        """

        super (CleanSignal, self).__init__(accumulator)

        if parent is not None:
            self.__parent = weakref.ref (parent, self.__orphan)
        else:
            self.__parent = None


    def orphan (self):
        """
        ‘Orphan’ the signal, i.e. set its parent to C{None}.  If the signal had a
        non-C{None} parent before and protected it from being garbage-collected, this
        protection is removed.
        """

        if self.__parent is not None:
            # Note that we must clear `__parent' first, because call to unprotect() below
            # can invoke our collect_garbage() which might then call unprotect() once more
            # (i.e. one time too many in result).
            self.__parent = None
            if self._handlers is not None:
                AbstractGCProtector.default.unprotect (self)

    def __orphan (self, reference = None):
        self.orphan ()


    def do_connect (self, handler):
        if self._handlers is None and self.__parent is not None:
            AbstractGCProtector.default.protect (self)

        super (CleanSignal, self).do_connect (handler)


    def disconnect (self, handler, *arguments, **keywords):
        if super (CleanSignal, self).disconnect (handler, *arguments, **keywords):
            if (    self._get_emission_level () == 0
                and self._handlers is None
                and self.__parent is not None):
                AbstractGCProtector.default.unprotect (self)

            return True

        else:
            return False

    def disconnect_all (self, handler, *arguments, **keywords):
        if super (CleanSignal, self).disconnect_all (handler, *arguments, **keywords):
            if (    self._get_emission_level () == 0
                and self._handlers is None
                and self.__parent is not None):
                AbstractGCProtector.default.unprotect (self)

            return True

        else:
            return False


    def _wrap_handler (self, handler, *arguments, **keywords):
        return WeakBinding.wrap (handler,
                                 arguments,
                                 self.__handler_garbage_collected,
                                 keywords)

    def __handler_garbage_collected (self, object):
        self.collect_garbage ()


    def collect_garbage (self):
        if self._handlers is not None and self._get_emission_level () == 0:
            # NOTE: This is essentially inlined method of the superclass.  While calling
            #       that method would be more proper, inlining it gives significant speed
            #       improvement.  Since it makes no difference for derivatives, we
            #       sacrifice "do what is right" principle in this case.

            self._handlers = [handler for handler in self._handlers
                              if handler is not None and (not isinstance (handler, WeakBinding)
                                                          or handler)]

            if not self._handlers:
                self._handlers = None
                if self.__parent is not None:
                    AbstractGCProtector.default.unprotect (self)


    def _additional_description (self, formatter):
        if self.__parent is not None:
            descriptions = ['parent: %s' % formatter (self.__parent ())]
        else:
            descriptions = []

        return descriptions + super (CleanSignal, self)._additional_description (formatter)



#-- Internal variables -----------------------------------------------

# It is not guaranteed to be a singleton, although it probably always is.
_EMPTY_TUPLE = ()



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
