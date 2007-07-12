#! /usr/bin/env python
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


import os
import sys

from benchmark import benchmarking


if not os.path.isfile (os.path.join ('notify', 'all.py')):
    sys.exit ("%s: cannot find '%s', strange..."
              % (sys.argv[0], os.path.join ('notify', 'all.py')))


print 'Building extension...'

# FIXME: Is that portable enough?
if os.system ('python setup.py build') != 0:
    sys.exit (1)

print



class AllBenchmarks (object):

    def __init__(self):
        everything = benchmarking.BenchmarkSuite ()

        for module_name in ('emission', 'logical'):
            module = __import__('benchmark.%s' % module_name, globals (), locals (), ('*',))

            setattr (self, module_name, module)
            everything.append (benchmarking.load_benchmarks (module))

        setattr (self, 'everything', everything)


benchmarking.main (AllBenchmarks (), 'everything')



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
