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


# This example demonstrates several features of conditions.  In particular, type
# derivation, compound logical conditions, predicates over variables and watcher
# condition.
#
# Currently you need custom classes, as shown below, to make conditions and variables
# really useful in GUI.  There are no plans to create a library over PyGTK or build
# condition/variable support into PyGTK or Kiwi at the moment, but I would welcome any
# such development.

# Implementation note: this example is written to work even with very old PyGTK versions.
# For instance, it doesn't use do_*() methods and connects handlers (for gobject signals,
# that is) instead.


import sys

if __name__ == '__main__':
    import os
    sys.path.insert (0, os.path.join (sys.path[0], os.pardir))


try:
    from notify.all import *
except ImportError:
    sys.exit ("Please build Py-notify by running 'python setup.py build' first")


import pygtk
pygtk.require ('2.0')

import gtk



class CheckButton (gtk.CheckButton):

    __Active = AbstractStateTrackingCondition.derive_type ('__Active', object = 'button',
                                                           getter = gtk.ToggleButton.get_active,
                                                           setter = gtk.ToggleButton.set_active)


    def __init__(self, label = None):
        gtk.CheckButton.__init__(self, label)
        self.active = CheckButton.__Active (self)
        self.connect ('toggled', lambda button: button.active.resynchronize_with_backend ())



class Entry (gtk.Entry):

    __Text = AbstractValueTrackingVariable.derive_type ('__Text', object = 'entry',
                                                        getter = gtk.Entry.get_text,
                                                        setter = gtk.Entry.set_text,
                                                        allowed_value_types = StringType)


    def __init__(self):
        gtk.Entry.__init__(self)
        self.text = Entry.__Text (self)
        self.connect ('changed', lambda entry: entry.text.resynchronize_with_backend ())



def create_markup_label (text):
    label = gtk.Label ()
    label.set_markup (text)

    return label



class Page (gtk.HBox):

    def __init__(self):
        gtk.HBox.__init__(self, False, 12)
        self.set_border_width (12)

        for widget in self.build_contents ():
            widget.show ()
            self.pack_start (widget, False)



class ConditionPage (Page):

    def build_contents (self):
        check_button = CheckButton ('Is true')
        self.condition = check_button.active

        yield check_button



class NotConditionPage (Page):

    def build_contents (self):
        check_button = CheckButton ('A is true')
        self.condition = ~check_button.active

        yield check_button
        yield create_markup_label ('<i>(true if A is false)</i>')



class AndConditionPage (Page):

    def build_contents (self):
        check_button1 = CheckButton ('A is true')
        check_button2 = CheckButton ('B is true')

        self.condition = check_button1.active & check_button2.active

        yield check_button1
        yield create_markup_label ('<i>and</i>')
        yield check_button2



class OrConditionPage (Page):

    def build_contents (self):
        check_button1 = CheckButton ('A is true')
        check_button2 = CheckButton ('B is true')

        self.condition = check_button1.active | check_button2.active

        yield check_button1
        yield create_markup_label ('<i>or</i>')
        yield check_button2



class XorConditionPage (Page):

    def build_contents (self):
        check_button1 = CheckButton ('A is true')
        check_button2 = CheckButton ('B is true')

        self.condition = check_button1.active ^ check_button2.active

        yield check_button1
        yield create_markup_label ('<i>xor</i>')
        yield check_button2



class IfElseConditionPage (Page):

    def build_contents (self):
        check_button1 = CheckButton ('A is true')
        check_button2 = CheckButton ('B is true')
        check_button3 = CheckButton ('C is true')

        self.condition = check_button1.active.if_else (check_button2.active, check_button3.active)

        yield check_button2
        yield create_markup_label ('<i>if</i>')
        yield check_button1
        yield create_markup_label ('<i>else</i>')
        yield check_button3



class PredicateConditionPage (Page):

    def build_contents (self):
        entry = Entry ()
        entry.text.set ('odd')

        self.condition = entry.text.predicate (lambda text: len (text) % 2 == 0)

        yield entry
        yield create_markup_label ('<i>true if text length is even</i>')



class ExampleWindow (gtk.Window):

    def __init__(self):
        gtk.Window.__init__(self)

        self.set_title ('Py-notify Example')
        self.set_resizable (False)
        self.set_border_width (12)

        self.__notebook = gtk.Notebook ()
        self.__notebook.set_tab_pos (gtk.POS_LEFT)

        self.__notebook.connect ('switch-page', self.__switch_page)

        self.__label = gtk.Label ()

        self.__watcher = WatcherCondition ()
        self.__watcher.store (self.__label.set_sensitive)
        self.__watcher.store (self.__update_label)

        box = gtk.VBox (False, 12)
        box.pack_start (self.__notebook)
        box.pack_start (self.__label, False)
        box.show_all ()

        self.add (box)

        self.__pages = []


    def add_page (self, label, page_class):
        page = page_class ()
        page.show ()
        self.__pages.append (page)

        self.__notebook.append_page (page, gtk.Label (label))


    def __update_label (self, state):
        self.__label.set_markup ('<big>Condition state is <b>%s</b></big>' % state)

    def __switch_page (self, notebook, page, page_index):
        self.__watcher.watch (self.__pages[page_index].condition)



example = ExampleWindow ()
example.connect ('destroy', lambda window: gtk.main_quit ())

example.add_page ('Condition', ConditionPage)
example.add_page ('Not',       NotConditionPage)
example.add_page ('And',       AndConditionPage)
example.add_page ('Or',        OrConditionPage)
example.add_page ('Xor',       XorConditionPage)
example.add_page ('If/else',   IfElseConditionPage)
example.add_page ('Predicate', PredicateConditionPage)

example.present ()
gtk.main ()



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
