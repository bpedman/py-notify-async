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


# TODO: Merge this file into `base.py' test file when Py-notify relies on Python 2.5 or
#       later.  Also use __get_changed_signal() once functions end in the proper class.



"""
Internal module used to implement Python 2.5 feautures of C{L{AbstractValueObject}} class.
I{Don’t import} this module directly: it is implementation detail and will be removed
eventually.
"""

__docformat__ = 'epytext en'
__all__       = ('storing', 'storing_safely', 'synchronizing', 'synchronizing_safely')


from contextlib import contextmanager



@contextmanager
def storing (self, handler, *arguments):
    self.store (handler, *arguments)

    try:
        yield self
    finally:
        self.changed.disconnect (handler, *arguments)


@contextmanager
def storing_safely (self, handler, *arguments):
    if self.store_safe (handler, *arguments):
        try:
            yield self
        finally:
            self.changed.disconnect (handler, *arguments)
    else:
        yield self


@contextmanager
def synchronizing (self, value_object, mediator = None):
    self.synchronize (value_object, mediator)

    try:
        yield self
    finally:
        self.desynchronize (value_object, mediator)


@contextmanager
def synchronizing_safely (self, value_object, mediator = None):
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
