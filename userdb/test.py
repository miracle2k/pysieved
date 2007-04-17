#! /usr/bin/python

## pysieved - Python managesieve server
## Copyright (C) 2007 Neale Pickett

## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or (at
## your option) any later version.

## This program is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
## USA

import unittest
import passwd
import virtual

class Config:
    def __init__(self):
        self.d = {}

    def set(self, section, key, val):
        self.d['%s %s' % (section, key)] = val

    def get(self, section, key, default):
        return self.d.get('%s %s' % (section, key), default)

    getint = get
    getboolean = get


class UserDBTest(unittest.TestCase):
    def setUp(self):
        self.c = Config()

    def test_passwd(self):
        u = passwd.new(0, self.c)
        self.failUnlessEqual(u.lookup('neale'), '/home/neale')

    def test_virtual(self):
        self.c.set('Virtual', 'base', '/home')
        self.c.set('Virtual', 'uid', 5000)
        self.c.set('Virtual', 'gid', 5000)
        u = virtual.new(False, self.c)
        self.failUnlessEqual(u.lookup('neale'), '/home/neale')

if __name__ == '__main__':
    unittest.main()

