#! /usr/bin/env python
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


import os
import sys

from benchmark import benchmarking


if not os.path.isfile (os.path.join ('notify', 'all.py')):
    sys.exit ("%s: cannot find '%s', strange..."
              % (sys.argv[0], os.path.join ('notify', 'all.py')))



_extensions_built = False

def _build_extensions ():
    global _extensions_built

    if not _extensions_built:
        print ('Building extension...')

        # FIXME: Is that portable enough?
        if os.system ('python setup.py build_ext') != 0:
            sys.exit (1)

        _extensions_built = True



_BENCHMARK_MODULES = ('emission', 'logical')

def _import_module_benchmarks (module_name):
    _build_extensions ()
    module = __import__('benchmark.%s' % module_name, globals (), locals (), ('*',))
    return benchmarking.load_benchmarks (module)

def _create_benchmark_module_importer (module_name):
    return lambda: _import_module_benchmarks (module_name)

def _import_all_benchmarks ():
    everything = benchmarking.BenchmarkSuite ()
    for module_name in _BENCHMARK_MODULES:
        everything.append (_import_module_benchmarks (module_name))

    return everything
    

class AllBenchmarks (object):

    def __init__(self):
        self.everything = _import_all_benchmarks
        for module_name in _BENCHMARK_MODULES:
            setattr (self, module_name, _create_benchmark_module_importer (module_name))


class BenchmarkProgram (benchmarking.BenchmarkProgram):

    def run (self):
        _build_extensions ()
        benchmarking.BenchmarkProgram.run (self)


BenchmarkProgram (AllBenchmarks (), 'everything')



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
