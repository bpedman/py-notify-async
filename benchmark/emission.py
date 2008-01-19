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

from benchmark     import benchmarking
from notify.signal import Signal



if sys.version_info[0] >= 3:
    xrange = range



_NUM_EMISSIONS = 100000


class EmissionBenchmark1 (benchmarking.Benchmark):

    def initialize (self):
        signal = Signal ()

        signal.connect (_ignoring_handler)
        signal.connect (_ignoring_handler, 1)
        signal.connect (_ignoring_handler, 'a', 'b')
        signal.connect (_ignoring_handler, None, True, False)

        self.__signal = signal


    def get_description (self, scale = 1.0):
        return '%d emissions of a signal with 4 function handlers' % int (scale * _NUM_EMISSIONS)


    def execute (self, scale = 1.0):
        signal = self.__signal

        for k in xrange (0, int (scale * _NUM_EMISSIONS)):
            signal ()


class EmissionBenchmark2 (benchmarking.Benchmark):

    def initialize (self):
        signal = Signal ()
        object = _Dummy ()

        signal.connect (object.ignoring_handler)
        signal.connect (object.ignoring_handler, 1)
        signal.connect (object.ignoring_handler, 'a', 'b')
        signal.connect (object.ignoring_handler, None, True, False)

        self.__signal = signal

        # To keep it alive.
        self.__object = object


    def get_description (self, scale = 1.0):
        return '%d emissions of a signal with 4 method handlers' % int (scale * _NUM_EMISSIONS)


    def execute (self, scale = 1.0):
        signal = self.__signal

        for k in xrange (0, int (scale * _NUM_EMISSIONS)):
            signal ()



try:
    import pygtk
    pygtk.require ('2.0')

    import gtk

    class GObjectEmissionBenchmark1 (benchmarking.Benchmark):

        def initialize (self):
            adjustment = gtk.Adjustment ()

            adjustment.connect ('changed', _ignoring_handler)
            adjustment.connect ('changed', _ignoring_handler, 1)
            adjustment.connect ('changed', _ignoring_handler, 'a', 'b')
            adjustment.connect ('changed', _ignoring_handler, None, True, False)

            self.__adjustment = adjustment


        def get_description (self, scale = 1.0):
            return ("%d emissions of gtk.Adjustment 'changed' signal with 4 function handlers"
                    % int (scale * _NUM_EMISSIONS))

        def get_version (self):
            return '.'.join (map (lambda x: str (x), gtk.pygtk_version))


        def execute (self, scale):
            adjustment = self.__adjustment

            for k in xrange (0, int (scale * _NUM_EMISSIONS)):
                adjustment.emit ('changed')



    class GObjectEmissionBenchmark2 (benchmarking.Benchmark):

        def initialize (self):
            adjustment = gtk.Adjustment ()
            object     = _Dummy ()

            adjustment.connect ('changed', object.ignoring_handler)
            adjustment.connect ('changed', object.ignoring_handler, 1)
            adjustment.connect ('changed', object.ignoring_handler, 'a', 'b')
            adjustment.connect ('changed', object.ignoring_handler, None, True, False)

            self.__adjustment = adjustment

            # To keep it alive.
            self.__object = object


        def get_description (self, scale = 1.0):
            return ("%d emissions of gtk.Adjustment 'changed' signal with 4 method handlers"
                    % int (scale * _NUM_EMISSIONS))

        def get_version (self):
            return '.'.join (map (lambda x: str (x), gtk.pygtk_version))


        def execute (self, scale):
            adjustment = self.__adjustment

            for k in xrange (0, int (scale * _NUM_EMISSIONS)):
                adjustment.emit ('changed')

except ImportError:
    pass



def _ignoring_handler (*arguments):
    pass



class _Dummy (object):

    def ignoring_handler (*arguments):
        pass



if __name__ == '__main__':
    benchmarking.main ()



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
