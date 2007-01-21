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
        handler to C{L{disconnect <AbstractSignal.disconnect>}} method.  This is somewhat
        less efficient, but easier to use.

    In general, you should use whatever suits your needs better.  GObject signals are
    limited to C{GObject} class derivatives.

G{classtree AbstractSignal}
"""

__docformat__ = 'epytext en'
__all__       = ('AbstractSignal', 'Signal', 'CleanSignal')


import sys

from notify.bind  import *
from notify.utils import *



#-- Signal interface classes -----------------------------------------

class AbstractSignal (object):

    """
    Abstract interface all signal classes must implement.

    Methods of this interface can be roughly grouped into the following groups:

      - Query methods: C{L{has_handlers}} (or just C{L{__nonzero__}}) and
        C{L{count_handlers}}.

      - Adding and removing handlers: C{L{is_connected}}, C{L{connect}},
        C{L{connect_safe}}, C{L{do_connect}}, C{L{do_connect_safe}}, C{L{disconnect}} and
        C{L{disconnect_all}}

      - Blocking connected handlers from being invoked: C{L{is_blocked}}, C{L{block}} and
        C{L{unblock}}.

      - Emission: C{L{emit}} (or just C{L{__call__}}), C{L{get_emission_level}} and
        C{L{stop_emission}}.

      - Rarely needed: C{L{_wrap_handler}} and C{L{collect_garbage}}.
    """

    __slots__ = ()


    class AbstractAccumulator (object):

        """
        An accumulator of signal handlers results.  It may combine, alter or discard
        values, post-process values after all handlers run (or emission stops for some
        reason) or stop emission based on the values.

        Note that accumulator should I{not} contain the accumulated value or have any
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

            @rtype: object
            """

            return None

        def accumulate_value (self, accumulated_value, value_to_add):
            """
            Accumulate C{value_to_add} into C{accumulated_value} and return the result.
            Result will be passed to next invocation of this method, if any.

            @rtype: object
            """

            raise_not_implemented_exception (self)

        def should_continue (self, accumulated_value):
            """
            Examine C{accumulated_value} and decide if signal emission should continue.
            Default implementation always returns C{True}.

            @rtype:   bool
            @returns: Whether signal emission should continue.
            """

            return True

        def post_process_value (self, accumulated_value):
            """
            Post-process C{accumulated_value} and return new value.  This method is called
            after signal emission ends, either because there are no more handlers or it
            was stopped by C{L{should_continue}} or from outside, using
            C{L{AbstractSignal.stop_emission}} method.  Default implementation does
            nothing and returns C{accumulated_value} unchanged.

            @rtype: object
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


        def accumulated_value (self, accumulated_value, value_to_add):
            return value_to_add


    class ValueListAccumulator (AbstractAccumulator):

        """
        An accumulator that returns a list of all handler results.  If there are no
        handlers at all, emission result is an empty list.
        """

        __slots__ = ()


        def get_initial_value (self):
            return []

        def accumulated_value (self, accumulated_value, value_to_add):
            accumulated_value.append (value_to_add)


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

        @rtype:   bool
        @returns: C{True} if there are handlers or if there I{might} be handlers.
        """

        raise_not_implemented_exception (self)

    def __nonzero__(self):
        """
        Same as C{L{has_handlers}} method.

        @rtype:   bool
        @returns: C{True} if there are handlers or if there I{might} be handlers.
        """

        return self.has_handlers ()


    def count_handlers (self):
        """
        Get the full number of handlers connected to this signal.  This method might be
        (comparatively) slow.  Unless you really need an exact number, consider using
        C{L{has_handlers}} instead.  This method is called by package implementation only
        when creating string representation of a signal or L{value
        <base.AbstractValueObject>} based on it.

        @rtype:   int
        @returns: Total number of connected handlers.
        """

        raise_not_implemented_exception (self)


    def is_connected (self, handler, *arguments):
        """
        Determine if C{handler} with C{arguments} is connected to the signal.  Note that
        this method doesn’t detect if there are several handlers equal to C{handler}
        connected.

        @rtype: bool
        """

        raise_not_implemented_exception (self)

    def is_blocked (self, handler, *arguments):
        """
        Determine if C{handler} with C{arguments} is connected to the signal and blocked.
        Note that if there are several handlers equal to C{handler} connected, all are
        either blocked or non-blocked.

        @rtype: bool
        """

        raise_not_implemented_exception (self)


    def connect (self, handler, *arguments):
        self.do_connect (self._wrap_handler (handler, *arguments))

    def connect_safe (self, handler, *arguments):
        if not self.is_connected (handler, *arguments):
            self.do_connect (self._wrap_handler (handler, arguments))
            return True
        else:
            return False

    def _wrap_handler (self, handler, *arguments):
        return WeakBinding.wrap (handler, *arguments)


    def do_connect (self, handler):
        raise_not_implemented_exception (self)

    def do_connect_safe (self, handler):
        if not self.is_connected (handler):
            self.do_connect (handler)
            return True
        else:
            return False


    def disconnect (self, handler, *arguments):
        raise_not_implemented_exception (self)

    def disconnect_all (self, handler, *arguments):
        if self.disconnect (handler, *arguments):
            while self.disconnect (handler, *arguments):
                pass

            return True

        else:
            return False


    def block (self, handler, *arguments):
        """
        Block C{handler} with C{arguments} from being called during subsequent emissions.
        If C{handler} is not connected to the signal to begin with, do nothing and return
        C{False}.  Else return C{True}.  Note that since it is impossible to distinguish
        between equal handlers, if there are several handlers equal to C{handler} with
        C{arguments} connected, all get blocked.

        Blocked handlers can be later unblocked.  You need to call C{L{unblock}} exactly
        the same number of times as this method for a handler to be considered
        non-blocked.  This is usually what you want.

        @rtype:   bool
        @returns: C{True} if C{handler} has been blocked, C{False} if it is not connected
                  to begin with.
        """

        raise_not_implemented_exception (self)

    def unblock (self, handler, *arguments):
        """
        Unblock a C{handler} with C{arguments}.  If the C{handler} is not connected or is
        not blocked, do nothing and return C{False}.  Else decrement its ‘block counter’
        and return C{True} only if it becomes non-blocked as a result.  Note that handlers
        must be unblocked exactly the same number of times as blocked, to become
        non-blocked again.

        @rtype:   bool
        @returns: C{True} if C{handler} becomes non-blocked; C{False} if it is not even
                  connected or still remains blocked.
        """

        raise_not_implemented_exception (self)


    def emit (self, *arguments):
        """
        Invoke non-blocked handlers connected to C{self}, passing C{arguments} to them.
        Whether all handlers are called and the return value of this method are determined
        by semantics of derived class.  Normally, they are influenced by L{accumulator
        <AbstractAccumulator>} (if any) with which the signal was created.  Custom
        subclasses may supply different semantics.

        Note that if a given handler was connected to this signal with any arguments,
        C{arguments} to this method are I{appended} to those specified at connection time.

        @rtype:   object
        @returns: Value, determined by subclass and, possibly, by its
                  L{accumulator <AbstractAccumulator>}.
        """

        raise_not_implemented_exception (self)

    def __call__(self, *arguments):
        """
        Same as C{L{emit}} method.

        @rtype:   object
        @returns: Value, determined by subclass and, possibly, by its
                  L{accumulator <AbstractAccumulator>}.
        """
        return self.emit (*arguments)


    def get_emission_level (self):
        """
        Get the number of unfinished calls to C{L{emit}} method of this signal.  For
        instance, if this signal hasn’t been emitted at all, the return value will be 0.
        If called from a handler, return value will be at least 1—more if in recursive
        emission.

        @rtype: int
        """

        raise_not_implemented_exception (self)

    def stop_emission (self):
        """
        Stop the current emission of the signal.  If there is no emission in progress to
        begin with or if the current emission is already stopped with a call to this
        method, do nothing and return C{False}, else return C{True}.  Note two significant
        moments:

          1. This method only stops the latest emission, earlier ones proceed normally
             (this is relevant only to recursive emissions.)

          2. It is impossible to start a new emission before corresponding call to
             C{L{emit}} returns.  In particular,
                 >>> if signal.stop_emission ():
                 ...     signal.emit ()

             won’t cause new emission since current instance of C{emit} won’t have a
             chance to finish.

        @rtype:   bool
        @returns: C{True} if this method is a not yet stopped emission in progress.
        """

        raise_not_implemented_exception (self)


    def collect_garbage (self):
        pass



    def default_exception_handler (signal, exception, handler):
        if isinstance (exception, (SystemExit, KeyboardInterrupt)):
            raise exception
        else:
            sys.excepthook (*sys.exc_info ())


    def ignoring_exception_handler (signal, exception, handler):
        pass


    def printing_exception_handler (signal, exception, handler):
        sys.excepthook (*sys.exc_info ())


    def reraising_exception_handler (signal, exception, handler):
        raise exception


    default_exception_handler   = staticmethod (default_exception_handler)
    ignoring_exception_handler  = staticmethod (ignoring_exception_handler)
    printing_exception_handler  = staticmethod (printing_exception_handler)
    reraising_exception_handler = staticmethod (reraising_exception_handler)


    exception_handler           = default_exception_handler


    def __repr__(self):
        return self.__to_string (self.__class__.__name__)

    def __str__(self):
        return self.__to_string (self.__class__.__name__.split ('.') [-1])


    def __to_string (self, class_name):
        try:
            num_handlers = self.count_handlers ()

            if num_handlers > 0:
                handler_data = ' (%d handlers)' % num_handlers
            else:
                handler_data = ''

        except NotImplementedError:
            handler_data = ' (count_handlers() not implemented)'

        return '<%s object at 0x%x%s>' % (class_name, id (self), handler_data)



#-- Standard signal classes ------------------------------------------

class Signal (AbstractSignal):

    """
    Standard implementation of C{L{AbstractSignal}} interface.

    Signals can have L{accumulators <AbstractAccumulator>} for values, returned by its
    handlers.  By default, these values are just ignored.
    """


    # Note that standard signals cannot be weak-referenced.  Such
    # references must be a really weird thing to do, so if you really
    # need them, you should use your own `Signal' subclass.
    __slots__ = ('_handlers', '_blocked_handlers',
                 '_Signal__accumulator', '_Signal__emission_level')


    def __init__(self, accumulator = None):
        if not (accumulator is None or isinstance (accumulator, Signal.AbstractAccumulator)):
            raise TypeError ("you must provide a `Signal.AbstractAccumulator' or None")

        super (Signal, self).__init__()

        self._handlers         = None
        self._blocked_handlers = None
        self.__accumulator     = accumulator
        self.__emission_level  = 0


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


    def is_connected (self, handler, *arguments):
        if self._handlers is not None and callable (handler):
            if arguments:
                handler = Binding (handler, *arguments)

            return handler in self._handlers

        else:
            return False


    def is_blocked (self, handler, *arguments):
        if self._blocked_handlers is not None and callable (handler):
            if arguments:
                handler = Binding (handler, *arguments)

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


    def disconnect (self, handler, *arguments):
        if self._handlers is None or not callable (handler):
            return False

        if arguments:
            handler = Binding (handler, *arguments)

        for index, _handler in enumerate (self._handlers):
            if _handler == handler:
                if self.__emission_level == 0:
                    del self._handlers[index]
                else:
                    self._handlers[index] = None

                if (self._blocked_handlers is not None
                    and handler not in self._handlers[index:]):
                    # This is the last handler, need to make sure it is not listed in
                    # `_blocked_handlers'.
                    self._blocked_handlers = [_handler for _handler in self._blocked_handlers
                                              if _handler != handler]

                    if not self._blocked_handlers:
                        self._blocked_handlers = None

                return True

        return False


    # Overriden for efficiency.

    def disconnect_all (self, handler, *arguments):
        if self._handlers is None or not callable (handler):
            return False

        if arguments:
            handler = Binding (handler, *arguments)

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

        if any_removed and self._blocked_handlers is not None:
            self._blocked_handlers = [_handler for _handler in self._blocked_handlers
                                      if _handler != handler]

            if not self._blocked_handlers:
                self._blocked_handlers = None

        return any_removed


    # Note: we rely on the way remove() works to fulfill our blocking obligations.


    def block (self, handler, *arguments):
        if callable (handler) and self._handlers is not None:
            if arguments:
                handler = Binding (handler, *arguments)

            if handler in self._handlers:
                if self._blocked_handlers is not None:
                    self._blocked_handlers.append (handler)
                else:
                    self._blocked_handlers = [handler]

                return True

        return False


    def unblock (self, handler, *arguments):
        if self._blocked_handlers is None or not callable (handler):
            return False

        if arguments:
            handler = Binding (handler, *arguments)

        try:
            self._blocked_handlers.remove (handler)

            if not self._blocked_handlers:
                self._blocked_handlers = None

            return True

        except:
            # It is not blocked to begin with.
            return False


    def emit (self, *arguments):
        if self._handlers is None or self.__emission_level < 0:
            return None

        if self.__accumulator is None:
            value = None
        else:
            value = self.__accumulator.get_initial_value ()

        if self._blocked_handlers is None:
            blocked_handlers = ()
        else:
            blocked_handlers = self._blocked_handlers

        try:
            self.__emission_level += 1

            for index, handler in enumerate (self._handlers):
                # Disconnected or garbage-collected hanlders are temporary set to None.
                if handler is None or handler in blocked_handlers:
                    continue

                if isinstance (handler, WeakBinding) and not handler:
                    self._handlers[index] = None
                    continue

                if self.__emission_level < 0:
                    self.__emission_level = -self.__emission_level
                    break

                try:
                    handler_value = handler (*arguments)

                # To also catch old-style string-only exceptions.
                except:
                    AbstractSignal.exception_handler (self, sys.exc_info () [1], handler)
                    continue

                if self.__accumulator is not None:
                    value = self.__accumulator.accumulate_value (value, handler_value)

                    if not self.__accumulator.should_continue (value):
                        break

        finally:
            self.__emission_level -= 1

        if self.__emission_level == 0:
            # Inlined and simplified collect_garbage(), for efficiency.
            self._handlers = [handler for handler in self._handlers if handler]

            if not self._handlers:
                self._handlers = None

        if self.__accumulator is not None:
            value = self.__accumulator.post_process_value (value)

        return value


    def get_emission_level (self):
        return abs (self.__emission_level)

    def stop_emission (self):
        # Check if we are in emission at all or if emission is not stopped already.
        if self.__emission_level > 0:
            self.__emission_level = -self.__emission_level
            return True
        else:
            return False


    def collect_garbage (self):
        # Don't remove disconnected or garbage-collected handlers if in nested emission,
        # it will spoil emit() calls completely.
        if self._handlers is not None and self.__emission_level == 0:
            self._handlers = [handler for handler in self._handlers
                              if handler is not None and (not isinstance (handler, WeakBinding)
                                                          or handler)]

            if not self._handlers:
                self._handlers = None



class CleanSignal (Signal):

    """
    Subclass of C{L{Signal}} which wraps its handlers in such a way that garbage-collected
    ones are detected instantly.
    """

    __slots__ = ('__weakref__')


    def do_connect (self, handler):
        if self._handlers is None:
            mark_object_as_used (self)

        super (CleanSignal, self).do_connect (handler)


    def disconnect (self, handler, *arguments):
        if super (CleanSignal, self).disconnect (handler, *arguments):
            if self.get_emission_level () == 0 and self._handlers is None:
                mark_object_as_unused (self)

            return True

        else:
            return False

    def disconnect_all (self, handler, *arguments):
        if super (CleanSignal, self).disconnect_all (handler, *arguments):
            if self.get_emission_level () == 0 and self._handlers is None:
                mark_object_as_unused (self)

            return True

        else:
            return False


    def _wrap_handler (self, handler, *arguments):
        return WeakBinding.wrap (handler, arguments, self.__handler_garbage_collected)

    def __handler_garbage_collected (self, object):
        self.collect_garbage ();


    def collect_garbage (self):
        if self._handlers is not None and self.get_emission_level () == 0:
            if super (CleanSignal, self).collect_garbage () and self._handlers is None:
                mark_object_as_unused (self)


# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
