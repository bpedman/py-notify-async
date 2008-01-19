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



import gc
import optparse
import sys
import time

from benchmark.configobj import ConfigObj
from types               import FunctionType, ModuleType

import notify

from notify.utils        import raise_not_implemented_exception, ClassTypes, StringType


__all__ = ('main', 'load_benchmarks', 'Benchmark', 'BenchmarkSuite', 'BenchmarkProgram')



_NUM_RUNS = 5



def load_benchmarks (source, *benchmark_names):
    toplevel_names = {}

    for name in benchmark_names:
        parts = name.split ('.', 2)

        if len (parts) == 1:
            toplevel_names[parts[0]] = ()
        else:
            if parts[0] in toplevel_names:
                if toplevel_names[parts[0]]:
                    toplevel_names[parts[0]].append (parts[1])
            else:
                toplevel_names[parts[0]] = [parts[1]]

    suite = BenchmarkSuite ()

    if isinstance (source, ModuleType) or toplevel_names:
        if toplevel_names:
            subobjects = toplevel_names.keys ()
        else:
            subobjects = dir (source)

        for name in subobjects:
            object = getattr (source, name)

            if isinstance (object, FunctionType):
                object = object ()

            if isinstance (object, ClassTypes) and issubclass (object, Benchmark):
                suite.append (object ())
            elif isinstance (object, BenchmarkSuite):
                suite.append (object)
            elif isinstance (object, ModuleType):
                if toplevel_names:
                    suite.append (load_benchmarks (object, *toplevel_names[name]))

    else:
        raise TypeError ("unsupported 'source' type (%s)" % type (source))

    return suite



class Benchmark (object):

    def initialize (self):
        pass

    def get_description (self, scale):
        return ("Benchmark '%s.%s', with scale %s"
                % (self.__module__, self.__class__.__name__, scale))

    def get_version (self):
        return notify.__version__

    def execute (self, scale):
        raise_not_implemented_exception (self)

    def finalize (self):
        pass


    def run (self, scale, num_runs = _NUM_RUNS, silent = False):
        if not silent:
            sys.stdout.write ('%s\n' % self.get_description (scale))

        times = []

        for k in range (0, num_runs):
            self.initialize ()
            gc.disable ()

            start  = time.clock ()
            self.execute (scale)
            finish = time.clock ()

            gc.enable ()
            self.finalize ()

            times.append (finish - start)

        self.__time = min (times)

        if not silent:
            sys.stdout.write ('Executed in %s s\n\n' % self.__time)


    def has_been_run (self):
        try:
            self.get_time ()
            return True
        except:
            return False

    def get_time (self):
        return self.__time


    def get_full_name (benchmark):
        if isinstance (benchmark, Benchmark):
            return ('%s.%s-%s' % (benchmark.__module__,
                                  benchmark.__class__.__name__,
                                  benchmark.get_version ()))
        else:
            return None


    get_full_name = staticmethod (get_full_name)



class BenchmarkSuite (object):

    def __init__(self):
        self.__children = []


    def append (self, child):
        assert isinstance (child, (Benchmark, BenchmarkSuite))
        self.__children.append (child)


    def run (self, scale, num_runs = _NUM_RUNS, silent = False):
        for child in self.__children:
            child.run (scale, num_runs, silent)


    def __iter__(self):
        return iter (self.__children)



class BenchmarkProgram (object):

    def __init__(self, object = '__main__', default_benchmark_name = None):
        if isinstance (object, StringType):
            self.__object = __import__(object)
            for name_part in object.split ('.') [1:]:
                self.__object = getattr (self.__object, name_part)
        else:
            self.__object = object

        self.__default_benchmark_name = default_benchmark_name
        self.__options                = None

        self.load_benchmarks ()
        self.run ()


    def load_benchmarks (self):
        self.__options, benchmark_names = self.__build_parser ().parse_args ()

        if not benchmark_names and self.__default_benchmark_name:
            benchmark_names = (self.__default_benchmark_name,)

        self.__suite = BenchmarkSuite ()
        self.__suite.append (load_benchmarks (self.__object, *benchmark_names))


    def run (self):
        should_run_test = lambda test_or_suite: True

        if self.__options.output is None:
            silent  = False
        else:
            silent  = True
            results = ConfigObj (self.__options.output)

            if not self.__options.force:
                should_run_test = (lambda test_or_suite:
                                       BenchmarkProgram.__test_is_new (test_or_suite, results))

        num_runs = _NUM_RUNS

        if self.__options.num_runs is not None:
            num_runs = self.__options.num_runs

        if num_runs > 1 and not silent:
            sys.stdout.write (('Each benchmark is executed %d times '
                               'and the best performance is reported\n\n')
                              % _NUM_RUNS)

        self.__do_run (self.__suite, self.__options.scale, num_runs, silent, should_run_test)

        if silent:
            self.__store_results (self.__suite, results)
            results.write ()


    def __build_parser (self):
        parser = optparse.OptionParser ()

        parser.add_option ('-o', '--output')
        parser.add_option ('-f', '--force',    action = 'store_true', default = False)
        parser.add_option ('-r', '--num-runs', type   = 'int')
        parser.add_option ('-s', '--scale',    type   = 'float',      default = 1.0)

        return parser


    def __do_run (self, suite, scale, num_runs, silent, should_run_test):
        if not should_run_test (suite):
            return

        if isinstance (suite, BenchmarkSuite):
            for benchmark in suite:
                self.__do_run (benchmark, scale, num_runs, silent, should_run_test)

        elif isinstance (suite, Benchmark):
            suite.run (scale, num_runs)


    def __store_results (self, suite, results):
        if isinstance (suite, BenchmarkSuite):
            for benchmark in suite:
                self.__store_results (benchmark, results)

        elif isinstance (suite, Benchmark):
            if not suite.has_been_run ():
                return

            benchmark_name = Benchmark.get_full_name (suite)
            is_new_result  = True

            for section in results:
                for name in results[section]:
                    if name == benchmark_name:
                        results[section][name] = suite.get_time ()
                        is_new_result          = False

            if is_new_result:
                if 'NEW RESULTS' in results:
                    results['NEW RESULTS'][benchmark_name] = suite.get_time ()
                else:
                    results['NEW RESULTS'] = { benchmark_name: suite.get_time () }


    def __test_is_new (test_or_suite, results):
        if isinstance (test_or_suite, Benchmark):
            benchmark_name = Benchmark.get_full_name (test_or_suite)

            for section in results:
                if benchmark_name in results[section]:
                    return False

        return True


    __test_is_new = staticmethod (__test_is_new)


main = BenchmarkProgram



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
