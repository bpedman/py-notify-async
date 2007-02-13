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



import gc
import optparse
import sys
import time

from configobj    import ConfigObj
from types        import *

import notify

from notify.utils import *


__all__ = ('main', 'load_benchmarks', 'Benchmark', 'BenchmarkSuite', 'BenchmarkProgram')



_NUM_RUNS = 5



def load_benchmarks (source):
    if isinstance (source, FunctionType):
        source = source ()

    if isinstance (source, (Benchmark, BenchmarkSuite)):
        return source

    suite = BenchmarkSuite ()

    if isinstance (source, ModuleType):
        for name in dir (source):
            object = getattr (source, name)

            if isinstance (object, (ClassType, TypeType)) and issubclass (object, Benchmark):
                suite.append (object ())
            elif isinstance (object, BenchmarkSuite):
                suite.append (object)

    else:
        raise TypeError ("unsupported `source' type (%s)" % type (source))

    return suite



class Benchmark (object):

    def initialize (self):
        pass

    def get_description (self, scale):
        return ("Benchmark `%s.%s', with scale %s"
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

    def __init__(self, object = '__main__', benchmark_name = None):
        if isinstance (object, basestring):
            self.__object = __import__(object)
            for name_part in object.split ('.') [1:]:
                self.__object = getattr (self.__object, name_part)
        else:
            self.__object = object

        self.__benchmark_name = benchmark_name
        self.__options        = None

        self.load_benchmarks ()
        self.run ()


    def load_benchmarks (self):
        self.__options, benchmark_names = self.__build_parser ().parse_args ()

        if self.__benchmark_name is None:
            self.__suite = load_benchmarks (self.__object)

        else:
            self.__suite = BenchmarkSuite ()
            self.__suite.append (load_benchmarks (getattr (self.__object, self.__benchmark_name)))


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



# NOTE: Needed since standard parsers provided by `ConfigParser' module do not preserve
#       order.
class _ConfigurationParser (object):

    def __init__(self):
        self.__values = []


    def read (self, filename):
        if filename is None:
            return

        file = open (filename)

        try:
            section_name = None

            for line in file:
                line = line.strip ()

                if not line or line[0] == '#':
                    continue

                if line[0] == '[' and line[-1] == ']':
                    section_name = line[1:-1]

                    try:
                        self.add_section (section_name)
                    except:
                        pass

                    continue

                if section_name is not None:
                    name_value = line.split ('=', 2)

                    if len (name_value) == 2:
                        try:
                            self.set (section_name, name_value[0].strip (), value.strip ())
                        except:
                            pass

        finally:
            file.close ()
            print self.__values


    def write (self, filename):
        file = open (filename, 'w')

        try:
            for section_name, values in self.__values:
                file.write ('[%s]\n' % section_name)

                for name, value in values:
                    file.write ('%s = %s\n' % (name, value))

                file.write ('\n')

        finally:
            file.close ()


    def sections (self):
        return [section_name for section_name, values in self.__values]


    def has_section (self, section_name):
        return section_name in self.sections ()


    def add_section (self, section_name):
        if not self.has_section (section_name):
            self.__values.append ((section_name, []))
        else:
            raise ValueError ("there is already section named `%s'" % section_name)


    def items (self, section_name):
        for _name, values in self.__values:
            if _name == section_name:
                return tuple (values)

        raise ValueError ("there is no section named `%s'" % section_name)


    def set (self, section_name, value_name, new_value):
        print self.__values
        for _name, values in self.__values:
            if _name == section_name:
                for index, name_value in enumerate (values):
                    if name_value[0] == value_name:
                        values[index] = (value_name, new_value)
                        break
                else:
                    values.append ((value_name, new_value))

                print values, self.__values
                return

        raise ValueError ("there is no section named `%s'" % section_name)



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
