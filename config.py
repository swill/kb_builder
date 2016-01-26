# kb_builder builts keyboard plate and case CAD files using JSON input.
#
# Copyright (C) 2015  Will Stevens (swill)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os

config = {}

config['app'] = {}
config['app']['port'] = 80
config['app']['pwd'] = os.path.dirname(__file__)
config['app']['static'] = os.path.join(config['app']['pwd'], 'static')
config['app']['export'] = os.path.join(config['app']['static'], 'exports')
config['app']['formats'] = ['js', 'dxf', 'svg', 'brp', 'stp', 'stl', 'json']
# ^ remove formats to speed up build time
config['app']['debug'] = False
config['app']['log'] = './kb_builder.log'

config['lib'] = {}
config['lib']['freecad_lib_dir'] = "/usr/lib/freecad/lib"
config['lib']['freecad_mod_dir'] = ""
