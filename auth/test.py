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
import os
import pam
import sasl
import htpasswd
import tempfile
import crypt

class Config:
    def __init__(self):
        self.d = {}

    def set(self, section, key, val):
        self.d['%s %s' % (section, key)] = val

    def get(self, section, key, default):
        return self.d.get('%s %s' % (section, key), default)

    getint = get
    getboolean = get


class AuthTest(unittest.TestCase):
    def setUp(self):
        self.c = Config()
        self.user, self.passwd = os.environ['TEST_AUTH'].split(':')

    def attempt(self, module):
        u = module.new(0, self.c)
        self.failUnless(u.auth(self.user, self.passwd))
        self.failIf(u.auth(      self.user, '.' + self.passwd))
        self.failIf(u.auth('.' + self.user,       self.passwd))
        self.failIf(u.auth('.' + self.user, '.' + self.passwd))

    def test_pam(self):
        self.attempt(pam)

    def test_sasl(self):
        self.attempt(sasl)

    def test_htpasswd(self):
        f = tempfile.NamedTemporaryFile()
        for i in range(10):
            pw = crypt.crypt('pass%d', 'bm')
            f.write('wembly%d:%s\n' % (i, pw))
        f.write('%s:%s\n' % (self.user, crypt.crypt(self.passwd, 'aa')))
        f.flush()
        self.c.set('htpasswd', 'passwdfile', f.name)
        self.attempt(htpasswd)
