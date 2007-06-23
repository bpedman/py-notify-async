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
#       later.


from __future__       import with_statement

from contextlib       import nested

from notify.condition import *
from notify.variable  import *
from test.__common    import *


__all__ = ('BaseContextManagerTestCase',)



class BaseContextManagerTestCase (NotifyTestCase):

    def test_storing_1 (self):
        variable       = Variable ()
        self.results   = []

        variable.value = 100

        with variable.storing (self.simple_handler):
            variable.value = 200

        variable.value = 300

        self.assert_results (100, 200)


    def test_storing_2 (self):
        variable       = Variable ()
        self.results   = []

        variable.value = 100

        with nested (ignoring_exceptions (), variable.storing (self.simple_handler)):
            variable.value = 200
            raise Exception

        variable.value = 300

        self.assert_results (100, 200)


    def test_storing_safely_1 (self):
        variable       = Variable ()
        self.results   = []

        variable.value = 100

        with variable.storing_safely (self.simple_handler):
            variable.value = 200

            with variable.storing_safely (self.simple_handler):
                variable.value = 300

            variable.value = 400

        variable.value = 500

        self.assert_results (100, 200, 300, 400)


    def test_storing_safely_2 (self):
        variable       = Variable ()
        self.results   = []

        variable.value = 100

        with nested (ignoring_exceptions (), variable.storing_safely (self.simple_handler)):
            variable.value = 200

            with nested (ignoring_exceptions (), variable.storing_safely (self.simple_handler)):
                variable.value = 300

            variable.value = 400
            raise Exception

        variable.value = 500

        self.assert_results (100, 200, 300, 400)


    def test_synchronizing_1 (self):
        variable1       = Variable ()
        variable2       = Variable ()
        self.results    = []

        variable1.value = 100
        variable2.value = 200

        variable1.changed.connect (self.simple_handler)

        with variable1.synchronizing (variable2):
            variable2.value = 300

        variable2.value = 400

        self.assert_results (200, 300)


    def test_synchronizing_2 (self):
        variable1       = Variable ()
        variable2       = Variable ()
        self.results    = []

        variable1.value = 100
        variable2.value = 200

        variable1.changed.connect (self.simple_handler)

        with nested (ignoring_exceptions (), variable1.synchronizing (variable2)):
            variable2.value = 300
            raise Exception

        variable2.value = 400

        self.assert_results (200, 300)


    def test_synchronizing_safely_1 (self):
        variable1       = Variable ()
        variable2       = Variable ()
        self.results    = []

        variable1.value = 100
        variable2.value = 200

        variable1.changed.connect (self.simple_handler)

        variable1.synchronize (variable2)

        with variable1.synchronizing_safely (variable2):
            variable2.value = 300

        variable2.value = 400

        self.assert_results (200, 300, 400)


    def test_synchronizing_safely_2 (self):
        variable1       = Variable ()
        variable2       = Variable ()
        self.results    = []

        variable1.value = 100
        variable2.value = 200

        variable1.changed.connect (self.simple_handler)

        variable1.synchronize (variable2)

        with nested (ignoring_exceptions (), variable1.synchronizing_safely (variable2)):
            variable2.value = 300
            raise Exception

        variable2.value = 400

        self.assert_results (200, 300, 400)



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
