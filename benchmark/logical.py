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


if __name__ == '__main__':
    import os
    import sys

    sys.path.insert (0, os.path.join (sys.path[0], os.pardir))



import sys

from benchmark        import benchmarking
from notify.condition import Condition



if sys.version_info[0] >= 3:
    xrange = range



_NUM_ITERATIONS = 10000


class LogicalBenchmark1 (benchmarking.Benchmark):

    def initialize (self):
        self.__condition1 = Condition (False)
        self.__condition2 = Condition (False)
        self.__condition3 = Condition (False)
        self.__condition4 = Condition (False)
        self.__condition5 = Condition (False)

        self.__compound_condition = ((self.__condition1 & self.__condition2)
                                     .if_else (self.__condition3,
                                               self.__condition4 | ~self.__condition5))
        self.__compound_condition.changed.connect (_ignoring_handler)


    def get_description (self, scale = 1.0):
        return ('%d iterations of state changes in a complex compound conditions tree'
                % int (scale * _NUM_ITERATIONS))


    def execute (self, scale = 1.0):
        condition1 = self.__condition1
        condition2 = self.__condition2
        condition3 = self.__condition3
        condition4 = self.__condition4
        condition5 = self.__condition5

        for k in xrange (0, int (scale * _NUM_ITERATIONS)):
            # Changed order to increase number of state changes in
            # `self.__compound_condition' (the final condition.)

            condition1.state = True
            condition2.state = True
            condition3.state = True

            condition3.state = False
            condition2.state = False
            condition1.state = False

            condition5.state = True
            condition4.state = True

            condition4.state = False
            condition5.state = False



def _ignoring_handler (*arguments):
    pass



if __name__ == '__main__':
    benchmarking.main ()



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
