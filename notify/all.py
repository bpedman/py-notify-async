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


"""
An utility module that can be used to conveniently import all package classes at once.  It
would look like this:
    >>> from notify.all import *

Whether to use this feature is up to you.
"""

__docformat__ = 'epytext en'
__all__       = ()


for module_name in ('base', 'bind', 'condition', 'mediator', 'signal', 'variable', 'utils'):
    module = __import__('notify.%s' % module_name, globals (), locals (), '*')

    for name in module.__all__:
        globals () [name] = getattr (module, name)

    __all__ += module.__all__


del module_name
del module
del name



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
