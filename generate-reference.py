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
import re

from urlparse import urlunsplit


try:
    import epydoc.cli
except:
    sys.exit ('%s: epydoc is not found; get it from http://epydoc.sourceforge.net/'
              % sys.argv[0])


if not os.path.isfile (os.path.join ('notify', 'all.py')):
    sys.exit ("%s: cannot find '%s', strange..."
              % (sys.argv[0], os.path.join ('notify', 'all.py')))


print ('Building extension...')

# FIXME: Is that portable enough?
if os.system ('python setup.py build_ext') != 0:
    sys.exit (1)


print ('Invoking epydoc...')


output_directory = os.path.join ('docs', 'reference')
fast_mode        = 'fast' in sys.argv

if fast_mode:
    sys.argv.remove ('fast')

sys.argv.extend (['--name=Py-notify',
                  '--url=http://home.gna.org/py-notify/',
                  '--exclude=notify._2_5',
                  '--exclude=notify._2_x',
                  '--inheritance=grouped',
                  '--no-sourcecode',
                  '--css=%s'    % os.path.join ('docs', 'epydoc.css'),
                  '--output=%s' % output_directory])

if not fast_mode:
    sys.argv.append ('--graph=classtree')

sys.argv.append ('notify')

epydoc.cli.cli ()


print ('Post-processing generated HTML files...')


prompt_regex = re.compile ('<span class="(py-prompt|py-more)">([^<]*)</span>')

def replace_prompt (match_object):
    if '\n' in match_object.group (1):
        return '\n'
    else:
        return ''


paren_regex_1 = re.compile ('class="summary-sig-name">'
                            '([a-zA-Z_0-9]+\\.)*[a-zA-Z_0-9]*[a-zA-Z0-9]</a>\\(')
paren_regex_2 = re.compile ('class="(summary-)?sig-name">[a-zA-Z_0-9]*[a-zA-Z0-9]</span>\\(')

def replace_paren_1 (match_object):
    return match_object.group (0) [:-1] + ' ('

def replace_paren_2 (match_object):
    return match_object.group (0) [:-1] + ' ('


default_value_regex = re.compile ('>=<span class="(summary-)?sig-default">')

def replace_default_value (match_object):
    return '> = ' + match_object.group (0) [2:]


hr_regex = re.compile ('<hr */>')


for root, directories, filenames in os.walk (output_directory):
    for filename in filenames:
        if not filename.endswith ('.html'):
            continue

        file = open (os.path.join (root, filename))

        try:
            contents = ''.join (file.readlines ())
        finally:
            file.close ()

        # Prompts get in our way if we want to copy examples from docs to Python
        # interpreter.
        contents = prompt_regex .sub (replace_prompt,  contents)

        contents = paren_regex_1.sub (replace_paren_1, contents)
        contents = paren_regex_2.sub (replace_paren_2, contents)

        contents = default_value_regex.sub (replace_default_value, contents)

        # There is no charset name...
        contents = contents.replace ('</head>',
                                     '  <meta http-equiv="Content-Type" '
                                     'content="text/html; charset=utf-8" />\n</head>')
        contents = contents.replace (' - ', ' — ')

        contents = hr_regex.sub ('', contents)

        file = open (os.path.join (root, filename), 'w')

        try:
            file.write (contents)
        finally:
            file.close ()


print ("Reference has been generated in '%s'" % output_directory)
print ("Point your browser to %s"
       % urlunsplit (('file', None,
                      os.path.join (os.path.abspath (output_directory), 'index.html'),
                      None, None)))



# Local variables:
# mode: python
# python-indent: 4
# indent-tabs-mode: nil
# fill-column: 90
# End:
