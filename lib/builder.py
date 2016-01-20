#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
import json
import logging

import math
import os
import sys

from config import config as cfg

import FreeCAD
import cadquery
import importDXF
import importSVG
import Mesh
import Part

log = logging.getLogger()

if 'lib' in cfg and 'freecad_lib_dir' in cfg['lib'] and \
        cfg['lib']['freecad_lib_dir'] != "":
    sys.path.append(cfg['lib']['freecad_lib_dir'])
if 'lib' in cfg and 'freecad_mod_dir' in cfg['lib'] and \
        cfg['lib']['freecad_mod_dir'] != "":
    for mod in os.listdir(cfg['lib']['freecad_mod_dir']):
        mod_path = os.path.join(cfg['lib']['freecad_mod_dir'], mod)
        if os.path.isdir(mod_path):
            sys.path.append(mod_path)

SWITCH_LAYER = 'switch'
BOTTOM_LAYER = 'bottom'
CLOSED_LAYER = 'closed'
OPEN_LAYER = 'open'


class Plate(object):
    def __init__(self):
        self.UOM = "mm"
        self.width = 0
        self.height = 0
        self.thickness = 1.5
        self.fillet = 0
        self.kerf = 0.0
        self.x_pad = 0
        self.y_pad = 0
        self.x_off = 0
        self.grow_y = 0
        self.grow_x = 0
        self.u1 = 19.05
        self.switch_type = 1
        self.stab_type = 0
        self.stabs = {
            "300": 19.05,  # 3 unit
            "400": 28.575,  # 4 unit
            "450": 34.671,  # 4.5 unit
            "550": 42.8625,  # 5.5 unit
            "625": 50,  # 6.25 unit
            "650": 52.38,  # 6.5 unit
            "700": 57.15,  # 7 unit
            "800": 66.675,  # 8 unit
            "900": 66.675,  # 9 unit
            "1000": 66.675  # 10 unit
        }
        self.layout = []
        self.case = {'type': None}
        self.origin = (0, 0)
        self.usb_width = 10

    def set_x_pad(self, x):
        self.x_pad = x

    def set_y_pad(self, y):
        self.y_pad = y

    def set_thickness(self, t):
        self.thickness = t

    def set_fillet(self, f):
        self.fillet = f

    def set_kerf(self, k):
        self.kerf = k/2

    def set_switch_type(self, t):
        if t in range(5):
            log.info('Setting switch-type to %s', t)
            self.switch_type = t

    def set_stab_type(self, s):
        if s in range(3):
            log.info('Setting stab-type to %s', s)
            self.stab_type = s

    def set_poker_holes(self, d):
        self.case = {'type': 'poker', 'hole_diameter': d}

    def set_sandwich_holes(self, h, d):
        self.case = {'type': 'sandwich', 'holes': h, 'x_holes': 0,
                     'y_holes': 0, 'hole_diameter': d}

    # this is the main draw function for the class and handles the logical flow
    # and orchestration
    def draw(self, result, layout, data_hash, config):
        self.parse_layout(layout)
        p = self.init_plate()
        result['width'] = self.width
        result['height'] = self.height

        # cut the mount holes in the plate
        if not self.case['type']:
            p = self.center(p, -self.width/2 + self.kerf, -self.height/2 +
                            self.kerf)  # move to top left of the plate
        if self.case['type'] == 'poker':
            hole_points = [(-139, 9.2), (-117.3, -19.4), (-14.3, 0),
                           (48, 37.9), (117.55, -19.4), (139, 9.2)]  # holes
            rect_points = [(140.75, 9.2), (-140.75, 9.2)]  # edge slots
            rect_size = (3.5, 5)  # edge slot cutout to edge
            for c in hole_points:
                p = self.cut_hole(p, c,
                                  self.case['hole_diameter']).center(-c[0],
                                                                     -c[1])
            for c in rect_points:
                p = self.cut_rect(p, c, rect_size[0],
                                  rect_size[1]).center(-c[0], -c[1])
            p = self.center(p, -self.width/2 + self.kerf, -self.height/2 +
                            self.kerf)  # move to top left of the plate
        if self.case['type'] == 'sandwich':
            p = self.center(p, -self.width/2 + self.kerf, -self.height/2 +
                            self.kerf)  # move to top left of the plate
            if 'holes' in self.case and self.case['holes'] >= 4 and \
                    'x_holes' in self.case and 'y_holes' in self.case:
                self.layout_sandwich_holes()
                radius = self.case['hole_diameter']/2 - self.kerf
                x_gap = (self.width - self.x_pad - 2*self.kerf)/(self.case['x_holes'] + 1)
                y_gap = (self.height - self.y_pad - 2*self.kerf)/(self.case['y_holes'] + 1)
                p = p.center(self.x_pad/2, self.y_pad/2)
                for i in range(self.case['x_holes'] + 1):
                    p = p.center(x_gap, 0).circle(radius).cutThruAll()
                for i in range(self.case['y_holes'] + 1):
                    p = p.center(0, y_gap).circle(radius).cutThruAll()
                for i in range(self.case['x_holes'] + 1):
                    p = p.center(-x_gap, 0).circle(radius).cutThruAll()
                for i in range(self.case['y_holes'] + 1):
                    p = p.center(0, -y_gap).circle(radius).cutThruAll()
                if result['has_layers']:
                    self.export(p, result, BOTTOM_LAYER, data_hash, config)
                p = p.center(-self.x_pad/2, -self.y_pad/2)

        # cut all the switch and stabilizer openings...
        prev_width = None
        prev_y_off = 0
        for r, row in enumerate(self.layout):
            for k, key in enumerate(row):
                x, y, kx = 0, 0, 0
                if 'x' in key:
                    x = key['x']*self.u1
                    kx = x
                if 'y' in key and k == 0:
                    y = key['y']*self.u1
                if r == 0 and k == 0:
                    # handle placement of the first key in first row
                    p = self.center(p, key['w']*self.u1/2, self.u1/2)
                    x += self.x_pad
                    y += self.y_pad
                    # set x_off negative since the 'cut_switch' will append 'x'
                    # and we need to account inital spacing
                    self.x_off = -(x - (self.u1/2 + key['w']*self.u1/2) - kx)
                elif k == 0:  # handle changing rows
                    # move to the next row
                    p = self.center(p, -self.x_off, self.u1)
                    self.x_off = 0  # reset back to the left side of the plate
                    x += self.u1/2 + key['w']*self.u1/2
                else:  # handle all other keys
                    x += prev_width*self.u1/2 + key['w']*self.u1/2
                if prev_y_off != 0:  # prev_y_off != 0
                    y += -prev_y_off
                    prev_y_off = 0
                if 'h' in key and key['h'] > 1:  # deal with vertical keys
                    prev_y_off = key['h']*self.u1/2 - self.u1/2
                    y += prev_y_off
                p = self.cut_switch(p, (x, y), key)
                prev_width = key['w']
        self.export(p, result, SWITCH_LAYER, data_hash, config)

        # cut layers
        if result['has_layers']:
            # closed layer
            p = p.center(-self.origin[0], -self.origin[1])
            points = [
                (-self.width/2+self.x_pad+self.kerf*2,
                 -self.height/2+self.y_pad+self.kerf*2),
                (self.width/2-self.x_pad-self.kerf*2,
                 -self.height/2+self.y_pad+self.kerf*2),
                (self.width/2-self.x_pad-self.kerf*2,
                 self.height/2-self.y_pad-self.kerf*2),
                (-self.width/2+self.x_pad+self.kerf*2,
                 self.height/2-self.y_pad-self.kerf*2),
                (-self.width/2+self.x_pad+self.kerf*2,
                 -self.height/2+self.y_pad+self.kerf*2)
            ]
            p = p.polyline(points).cutThruAll()
            self.export(p, result, CLOSED_LAYER, data_hash, config)

            # open layer
            p = p.center(0, -self.height/2+self.y_pad/2+self.kerf)
            points = [
                (-self.usb_width/2+self.kerf, -self.y_pad/2-self.kerf),
                (self.usb_width/2-self.kerf, -self.y_pad/2-self.kerf),
                (self.usb_width/2-self.kerf, self.y_pad/2+self.kerf),
                (-self.usb_width/2+self.kerf, self.y_pad/2+self.kerf),
                (-self.usb_width/2+self.kerf, -self.y_pad/2-self.kerf)
            ]
            p = p.polyline(points).cutThruAll()
            self.export(p, result, OPEN_LAYER, data_hash, config)
        return result

    # parse the supplied layout to determine size and populate the properties
    # of each 'key'
    def parse_layout(self, layout):
        layout_width = 0
        layout_height = 0
        key_desc = False  # track if current is not a key and only describes the next key
        for row in layout:
            if isinstance(row, list):  # only handle arrays of keys
                row_width = 0
                row_height = 0
                row_layout = []
                for k in row:
                    key = {}
                    if isinstance(k, dict):  # descibes the next key
                        key = k
                        if 'w' not in key:
                            key['w'] = 1
                        if 'h' not in key:
                            key['h'] = 1
                        row_layout.append(key)
                        key_desc = True
                    else:
                        # is just a standard key (we know its a single unit
                        # key)
                        if not key_desc:
                            # only handle if it was not already handled as a
                            # key_desc
                            key['w'] = 1
                            key['h'] = 1
                            row_layout.append(key)
                        key_desc = False
                    if 'w' in key:
                        row_width += key['w']
                    if 'x' in key:
                        # offsets count towards total row width
                        row_width += key['x']
                    if 'y' in key:
                        row_height = key['y']
                self.layout.append(row_layout)
                if row_width > layout_width:
                    layout_width = row_width
                layout_height += self.u1 + row_height*self.u1
            # hidden global features
            if isinstance(row, dict):
                if 'grow_y' in row and (type(row['grow_y']) == int or
                                        type(row['grow_y']) == float):
                    self.grow_y = row['grow_y']/2
                if 'grow_x' in row and (type(row['grow_x']) == int or
                                        type(row['grow_x']) == float):
                    self.grow_x = row['grow_x']/2
        self.width = layout_width*self.u1 + 2*self.x_pad + 2*self.kerf
        self.height = layout_height + 2*self.y_pad + 2*self.kerf

    # initialize the plate object 'p' and get it ready to work with
    def init_plate(self):
        p = cadquery.Workplane("front").box(self.width, self.height,
                                            self.thickness)
        if self.fillet > 0:
            p = p.edges("|Z").fillet(self.fillet)
        return p.faces("<Z").workplane()

    # since the sandwich plate has a dynamic number of holes, determine where
    # the specified holes should be placed
    def layout_sandwich_holes(self):
        if 'holes' in self.case and self.case['holes'] >= 4 and 'x_holes' in self.case and 'y_holes' in self.case:
            holes = int(self.case['holes'])
            if holes % 2 == 0 and holes >= 4:
                # holes needs to be even and the first 4 are put in the corners
                x = self.width - self.x_pad - self.kerf  # x length to split
                y = self.height - self.y_pad - self.kerf  # y length to split
                # number of holes on each x side (not counting the corner
                # holes)
                _x = 0
                # number of holes on each y side (not counting the corner
                # holes)
                _y = 0
                # number of free holes to be placed on either x or y sides
                free = (holes-4)/2
                for f in range(free):
                    # loop through the available holes and place them
                    if x/(_x+1) == y/(_y+1):
                        # if equal, add the hole to the longer side
                        if x >= y:
                            _x += 1
                        else:
                            _y += 1
                    elif x/(_x+1) > y/(_y+1):
                        _x += 1
                    else:
                        _y += 1
                self.case['x_holes'] = _x
                self.case['y_holes'] = _y

    # take a set of points and rotate them 'r' degrees around 'a'
    def rotate_points(self, points, r, a):
        result = []
        for p in points:
            px = math.cos(math.radians(r)) * (p[0]-a[0]) - math.sin(math.radians(r)) * (p[1]-a[1]) + a[0]
            py = math.sin(math.radians(r)) * (p[0]-a[0]) + math.cos(math.radians(r)) * (p[1]-a[1]) + a[1]
            result.append((px, py))
        return result

    # cut a hole with center 'c' and diameter 'd'
    def cut_hole(self, p, c, d):
        p = self.center(p, c[0], c[1]).hole(d)
        return p

    # cut a rectangle with center 'c' with a width 'w' and heigh 'h'
    def cut_rect(self, p, c, w, h):
        p = self.center(p, c[0], c[1]).rect(w, h)
        return p

    # cut a switch opening with center 'c' defined by the 'key'
    def cut_switch(self, p, c, key=None):
        if not key:
            key = {}

        w = key['w'] if 'w' in key else 1
        h = key['h'] if 'h' in key else 1
        t = key['_t'] if '_t' in key and key['_t'] in range(4) else self.switch_type
        s = key['_s'] if '_s' in key and key['_s'] in range(2) else self.stab_type
        k = key['_k']/2 if '_k' in key else self.kerf
        r = key['_r'] if '_r' in key else None
        rs = key['_rs'] if '_rs' in key else None

        # cut switch cutout
        rotate = None
        if 'h' in key and h > w:
            rotate = True
        points = []
        if t == 0:  # standard square switch
            points = [
                (7-k+self.grow_x, -7+k-self.grow_y),
                (7-k+self.grow_x, 7-k+self.grow_y),
                (-7+k-self.grow_x, 7-k+self.grow_y),
                (-7+k-self.grow_x, -7+k-self.grow_y),
                (7-k+self.grow_x, -7+k-self.grow_y)
            ]
        elif t == 1:  # mx and alps compatible switch, mx can open
            points = [
                (7-k, -7+k), (7-k, -6.4+k), (7.8-k, -6.4+k), (7.8-k, 6.4-k),
                (7-k, 6.4-k), (7-k, 7-k), (-7+k, 7-k), (-7+k, 6.4-k),
                (-7.8+k, 6.4-k), (-7.8+k, -6.4+k), (-7+k, -6.4+k),
                (-7+k, -7+k), (7-k, -7+k)
            ]
        elif t == 2:  # mx switch can open (side wings)
            points = [
                (7-k, -7+k), (7-k, -6+k), (7.8-k, -6+k), (7.8-k, -2.9-k),
                (7-k, -2.9-k), (7-k, 2.9+k), (7.8-k, 2.9+k), (7.8-k, 6-k),
                (7-k, 6-k), (7-k, 7-k), (-7+k, 7-k), (-7+k, 6-k),
                (-7.8+k, 6-k), (-7.8+k, 2.9+k), (-7+k, 2.9+k), (-7+k, -2.9-k),
                (-7.8+k, -2.9-k), (-7.8+k, -6+k), (-7+k, -6+k), (-7+k, -7+k),
                (7-k, -7+k)
            ]
        elif t == 3:
            # rotatable mx switch can open both ways (side and top/bottom
            # wings)
            points = [
                (7-k, -7+k), (7-k, -6+k), (7.8-k, -6+k), (7.8-k, -2.9-k),
                (7-k, -2.9-k), (7-k, 2.9+k), (7.8-k, 2.9+k), (7.8-k, 6-k),
                (7-k, 6-k), (7-k, 7-k), (6-k, 7-k), (6-k, 7.8-k),
                (2.9+k, 7.8-k), (2.9+k, 7-k), (-2.9-k, 7-k), (-2.9-k, 7.8-k),
                (-6+k, 7.8-k), (-6+k, 7-k), (-7+k, 7-k), (-7+k, 6-k),
                (-7.8+k, 6-k), (-7.8+k, 2.9+k), (-7+k, 2.9+k), (-7+k, -2.9-k),
                (-7.8+k, -2.9-k), (-7.8+k, -6+k), (-7+k, -6+k), (-7+k, -7+k),
                (-6+k, -7+k), (-6+k, -7.8+k), (-2.9-k, -7.8+k), (-2.9-k, -7+k),
                (2.9+k, -7+k), (2.9+k, -7.8+k), (6-k, -7.8+k), (6-k, -7+k),
                (7-k, -7+k)
            ]
        elif t == 4:  # alps compatible switch, not MX compatible
            points = [
                (7.75-k, -6.4+k), (7.75-k, 6.4-k),
                (-7.75+k, 6.4-k), (-7.75+k, -6.4+k),
                (7.75-k, -6.4+k),
            ]
        if rotate:
            points = self.rotate_points(points, 90, (0, 0))
        if r:
            points = self.rotate_points(points, r, (0, 0))
        p = self.center(p, c[0], c[1]).polyline(points).cutThruAll()

        # cut 2 unit stabilizer cutout
        #   2 unit stabilizer
        if (w >= 2 and w < 3) or (rotate and h >= 2 and h < 3):
            if s == 0:
                # modified mx cherry spec 2u stabilizer to support costar
                points = [
                    (7-k, -7+k), (7-k, -4.73+k), (8.575+k, -4.73+k),
                    (8.575+k, -5.53+k), (10.3+k, -5.53+k), (10.3+k, -6.45+k),
                    (13.6-k, -6.45+k), (13.6-k, -5.53+k), (15.225-k, -5.53+k),
                    (15.225-k, -2.3+k), (16.1-k, -2.3+k), (16.1-k, 0.5-k),
                    (15.225-k, 0.5-k), (15.225-k, 6.77-k), (13.6-k, 6.77-k),
                    (13.6-k, 7.75-k), (10.3+k, 7.75-k), (10.3+k, 6.77-k),
                    (8.575+k, 6.77-k), (8.575+k, 5.97-k), (7-k, 5.97-k),
                    (7-k, 7-k), (-7+k, 7-k), (-7+k, 5.97-k),
                    (-8.575-k, 5.97-k), (-8.575-k, 6.77-k), (-10.3-k, 6.77-k),
                    (-10.3-k, 7.75-k), (-13.6+k, 7.75-k), (-13.6+k, 6.77-k),
                    (-15.225+k, 6.77-k), (-15.225+k, 0.5-k), (-16.1+k, 0.5-k),
                    (-16.1+k, -2.3+k), (-15.225+k, -2.3+k),
                    (-15.225+k, -5.53+k), (-13.6+k, -5.53+k),
                    (-13.6+k, -6.45+k), (-10.3-k, -6.45+k), (-10.3-k, -5.53+k),
                    (-8.575-k, -5.53+k), (-8.575-k, -4.73+k), (-7+k, -4.73+k),
                    (-7+k, -7+k), (7-k, -7+k)
                ]
                if rotate:
                    points = self.rotate_points(points, 90, (0, 0))
                if rs:
                    points = self.rotate_points(points, rs, (0, 0))
                p = p.polyline(points).cutThruAll()
            if s == 1:
                # cherry spec 2u stabilizer
                points = [
                    (7-k, -7+k), (7-k, -4.73+k), (8.575+k, -4.73+k),
                    (8.575+k, -5.53+k), (15.225-k, -5.53+k),
                    (15.225-k, -2.3+k), (16.1-k, -2.3+k), (16.1-k, 0.5-k),
                    (15.225-k, 0.5-k), (15.225-k, 6.77-k), (13.6-k, 6.77-k),
                    (13.6-k, 7.97-k), (10.3+k, 7.97-k), (10.3+k, 6.77-k),
                    (8.575+k, 6.77-k), (8.575+k, 5.97-k), (7-k, 5.97-k),
                    (7-k, 7-k), (-7+k, 7-k), (-7+k, 5.97-k),
                    (-8.575-k, 5.97-k), (-8.575-k, 6.77-k), (-10.3-k, 6.77-k),
                    (-10.3-k, 7.97-k), (-13.6+k, 7.97-k), (-13.6+k, 6.77-k),
                    (-15.225+k, 6.77-k), (-15.225+k, 0.5-k), (-16.1+k, 0.5-k),
                    (-16.1+k, -2.3+k), (-15.225+k, -2.3+k),
                    (-15.225+k, -5.53+k), (-8.575-k, -5.53+k),
                    (-8.575-k, -4.73+k), (-7+k, -4.73+k), (-7+k, -7+k),
                    (7-k, -7+k)
                ]
                if rotate:
                    points = self.rotate_points(points, 90, (0, 0))
                if rs:
                    points = self.rotate_points(points, rs, (0, 0))
                p = p.polyline(points).cutThruAll()
            if s == 2:
                # costar stabilizers only
                points_l = [(-10.3-k, -6.45+k), (-13.6+k, -6.45+k),
                            (-13.6+k, 7.75-k), (-10.3-k, 7.75-k),
                            (-10.3-k, -6.45+k)]
                points_r = [(10.3+k, -6.45+k), (13.6-k, -6.45+k),
                            (13.6-k, 7.75-k), (10.3+k, 7.75-k),
                            (10.3+k, -6.45+k)]
                if rotate:
                    points_l = self.rotate_points(points_l, 90, (0, 0))
                    points_r = self.rotate_points(points_r, 90, (0, 0))
                if rs:
                    points_l = self.rotate_points(points_l, rs, (0, 0))
                    points_r = self.rotate_points(points_r, rs, (0, 0))
                p = p.polyline(points_l).cutThruAll()
                p = p.polyline(points_r).cutThruAll()

        # cut spacebar stabilizer cutout
        if (w >= 3) or (rotate and h >= 3):
            l = w
            if rotate:
                l = h
            x = 11.95  # default to a 2unit stabilizer if not found...
            # use the length of the key to determine if we have a known
            # stabilizer config for that key
            stab_size = '%s' % (str(l).replace('.', '').ljust(3, '0') if l < 10 else str(l).replace('.', '').ljust(4, '0'))
            if stab_size in self.stabs:
                x = self.stabs[stab_size]
            if s == 0:
                # modified mx cherry spec stabilizer to support costar
                points = [
                    (7-k, -7+k), (7-k, -2.3+k), (x-3.325+k, -2.3+k),
                    (x-3.325+k, -5.53+k), (x-1.65+k, -5.53+k),
                    (x-1.65+k, -6.45+k), (x+1.65-k, -6.45+k),
                    (x+1.65-k, -5.53+k), (x+3.325-k, -5.53+k),
                    (x+3.325-k, -2.3+k), (x+4.2-k, -2.3+k), (x+4.2-k, 0.5-k),
                    (x+3.325-k, 0.5-k), (x+3.325-k, 6.77-k),
                    (x+1.65-k, 6.77-k), (x+1.65-k, 7.75-k), (x-1.65+k, 7.75-k),
                    (x-1.65+k, 6.77-k), (x-3.325+k, 6.77-k),
                    (x-3.325+k, 2.3-k), (7-k, 2.3-k), (7-k, 7-k), (-7+k, 7-k),
                    (-7+k, 2.3-k), (-x+3.325-k, 2.3-k), (-x+3.325-k, 6.77-k),
                    (-x+1.65-k, 6.77-k), (-x+1.65-k, 7.75-k),
                    (-x-1.65+k, 7.75-k), (-x-1.65+k, 6.77-k),
                    (-x-3.325+k, 6.77-k), (-x-3.325+k, 0.5-k),
                    (-x-4.2+k, 0.5-k), (-x-4.2+k, -2.3+k),
                    (-x-3.325+k, -2.3+k), (-x-3.325+k, -5.53+k),
                    (-x-1.65+k, -5.53+k), (-x-1.65+k, -6.45+k),
                    (-x+1.65-k, -6.45+k), (-x+1.65-k, -5.53+k),
                    (-x+3.325-k, -5.53+k), (-x+3.325-k, -2.3+k),
                    (-7+k, -2.3+k), (-7+k, -7+k), (7-k, -7+k)
                ]
                if rotate:
                    points = self.rotate_points(points, 90, (0, 0))
                if rs:
                    points = self.rotate_points(points, rs, (0, 0))
                p = p.polyline(points).cutThruAll()
            if s == 1:
                # cherry spec spacebar stabilizer
                points = [
                    (7-k, -7+k), (7-k, -2.3+k), (x-3.325+k, -2.3+k),
                    (x-3.325+k, -5.53+k), (x+3.325-k, -5.53+k),
                    (x+3.325-k, -2.3+k), (x+4.2-k, -2.3+k), (x+4.2-k, 0.5-k),
                    (x+3.325-k, 0.5-k), (x+3.325-k, 6.77-k),
                    (x+1.65-k, 6.77-k), (x+1.65-k, 7.97-k), (x-1.65+k, 7.97-k),
                    (x-1.65+k, 6.77-k), (x-3.325+k, 6.77-k),
                    (x-3.325+k, 2.3-k), (7-k, 2.3-k), (7-k, 7-k), (-7+k, 7-k),
                    (-7+k, 2.3-k), (-x+3.325-k, 2.3-k), (-x+3.325-k, 6.77-k),
                    (-x+1.65-k, 6.77-k), (-x+1.65-k, 7.97-k),
                    (-x-1.65+k, 7.97-k), (-x-1.65+k, 6.77-k),
                    (-x-3.325+k, 6.77-k), (-x-3.325+k, 0.5-k),
                    (-x-4.2+k, 0.5-k), (-x-4.2+k, -2.3+k),
                    (-x-3.325+k, -2.3+k), (-x-3.325+k, -5.53+k),
                    (-x+3.325-k, -5.53+k), (-x+3.325-k, -2.3+k),
                    (-7+k, -2.3+k), (-7+k, -7+k), (7-k, -7+k)
                ]
                if rotate:
                    points = self.rotate_points(points, 90, (0, 0))
                if rs:
                    points = self.rotate_points(points, rs, (0, 0))
                p = p.polyline(points).cutThruAll()
            if s == 2:
                # costar stabilizers only
                points_l = [(-x+1.65-k, -6.45+k), (-x-1.65+k, -6.45+k),
                            (-x-1.65+k, 7.75-k), (-x+1.65-k, 7.75-k),
                            (-x+1.65-k, -6.45+k)]
                points_r = [(x-1.65+k, -6.45+k), (x+1.65-k, -6.45+k),
                            (x+1.65-k, 7.75-k), (x-1.65+k, 7.75-k),
                            (x-1.65+k, -6.45+k)]
                if rotate:
                    points_l = self.rotate_points(points_l, 90, (0, 0))
                    points_r = self.rotate_points(points_r, 90, (0, 0))
                if rs:
                    points_l = self.rotate_points(points_l, rs, (0, 0))
                    points_r = self.rotate_points(points_r, rs, (0, 0))
                p = p.polyline(points_l).cutThruAll()
                p = p.polyline(points_r).cutThruAll()
        self.x_off += c[0]
        return p

    # sets the center and also records the relative distance it moved in
    # relation to 'origin'
    def center(self, p, x, y):
        _x = self.origin[0]
        _y = self.origin[1]
        self.origin = (_x+x, _y+y)
        return p.center(x, y)

    def __repr__(self):
        '''Print out all Plate object configuration settings.'''

        settings = {}

        settings['plate_layout'] = self.layout
        settings['switch_type'] = self.switch_type
        settings['stabilizer_type'] = self.stab_type
        settings['case_type_and_holes'] = self.case
        settings['width_padding'] = self.x_pad
        settings['height_padding'] = self.y_pad
        settings['plate_corners'] = self.fillet
        settings['kerf'] = self.kerf
        # XXX line colour?

        return json.dumps(settings, sort_keys=True, indent=4,
                          separators=(',', ': '))

    def export(self, p, result, label, data_hash, config):
        # export the plate to different file formats
        log.info("Exporting %s layer for %s" % (label, data_hash))
        # draw the part so we can export it
        Part.show(p.val().wrapped)
        doc = FreeCAD.ActiveDocument
        # export the drawing into different formats
        #   the absolute part of the working directory (aka - outside the web
        #   space)
        pwd_len = len(config['app']['pwd'])
        result['exports'][label] = []
        if 'js' in result['formats']:
            with open("%s/%s_%s.js" % (config['app']['export'], label,
                                       data_hash), "w") as f:
                cadquery.exporters.exportShape(p, 'TJS', f)
                result['exports'][label].append(
                    {'name': 'js', 'url': '%s/%s_%s.js' %
                        (config['app']['export'][pwd_len:], label, data_hash)})
                log.info("Exported 'JS'")
        if 'brp' in result['formats']:
            Part.export(doc.Objects, "%s/%s_%s.brp" %
                        (config['app']['export'], label, data_hash))
            result['exports'][label].append(
                {'name': 'brp', 'url': '%s/%s_%s.brp' %
                    (config['app']['export'][pwd_len:], label, data_hash)})
            log.info("Exported 'BRP'")
        if 'stp' in result['formats']:
            Part.export(doc.Objects, "%s/%s_%s.stp" %
                        (config['app']['export'], label, data_hash))
            result['exports'][label].append(
                {'name': 'stp', 'url': '%s/%s_%s.stp' %
                    (config['app']['export'][pwd_len:], label, data_hash)})
            log.info("Exported 'STP'")
        if 'stl' in result['formats']:
            Mesh.export(doc.Objects, "%s/%s_%s.stl" %
                        (config['app']['export'], label, data_hash))
            result['exports'][label].append(
                {'name': 'stl', 'url': '%s/%s_%s.stl' %
                    (config['app']['export'][pwd_len:], label, data_hash)})
            log.info("Exported 'STL'")
        if 'dxf' in result['formats']:
            importDXF.export(doc.Objects, "%s/%s_%s.dxf" %
                             (config['app']['export'], label, data_hash))
            result['exports'][label].append(
                {'name': 'dxf', 'url': '%s/%s_%s.dxf' %
                    (config['app']['export'][pwd_len:], label, data_hash)})
            log.info("Exported 'DXF'")
        if 'svg' in result['formats']:
            importSVG.export(doc.Objects, "%s/%s_%s.svg" %
                             (config['app']['export'], label, data_hash))
            result['exports'][label].append(
                {'name': 'svg', 'url': '%s/%s_%s.svg' %
                    (config['app']['export'][pwd_len:], label, data_hash)})
            log.info("Exported 'SVG'")
        if 'json' in result['formats'] and label == SWITCH_LAYER:
            with open("%s/%s_%s.json" % (config['app']['export'], label,
                      data_hash), 'w') as json_file:
                json_file.write(repr(self))
            result['exports'][label].append(
                {'name': 'json', 'url': '%s/%s_%s.json' %
                    (config['app']['export'][pwd_len:], label, data_hash)})
            log.info("Exported 'JSON'")
        # remove all the documents from the view before we move on
        for o in doc.Objects:
            doc.removeObject(o.Label)


# take the input from the webserver and instantiate and draw the plate
def build(data_hash, data, config):
    # create the result object
    #   Have to use a copy in case we remove SVG later
    result = {}
    result['has_layers'] = False
    result['plates'] = [SWITCH_LAYER]
    result['formats'] = cfg['app']['formats'][:]
    result['exports'] = {}
    p = Plate()
    if 'case-type' in data:
        if data['case-type'] == 'poker':
            if 'mount-holes-size' in data:
                p.set_poker_holes(float(data['mount-holes-size']))
        if data['case-type'] == 'sandwich':
            result['plates'] = result['plates'] + [OPEN_LAYER, CLOSED_LAYER,
                                                   BOTTOM_LAYER]
            result['has_layers'] = True
            if 'mount-holes-num' in data and 'mount-holes-size' in data:
                p.set_sandwich_holes(int(data['mount-holes-num']),
                                     float(data['mount-holes-size']))
    if 'switch-type' in data:
        p.set_switch_type(int(data['switch-type']))
    if 'stab-type' in data:
        p.set_stab_type(int(data['stab-type']))
    if 'width-padding' in data:
        p.set_x_pad(float(data['width-padding']))
    if 'height-padding' in data:
        p.set_y_pad(float(data['height-padding']))
    if 'fillet' in data:
        p.set_fillet(float(data['fillet']))
    if 'thickness' in data:
        p.set_thickness(float(data['thickness']))
    if 'kerf' in data:
        p.set_kerf(float(data['kerf']))
    if 'export_svg' in data and not data['export_svg']:
        result['formats'].remove('svg')
    # draw the plate
    result = p.draw(result, data['layout'], data_hash, config)
    log.info("Finished drawing: %s" % (data_hash))
    return result  # return the metadata result to the webserver
