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

import __init__
import warnings

class ScriptStorage(__init__.ScriptStorage):
    def __init__(self):
        self.scripts = {}
        self.active = None

    def __setitem__(self, k, v):
        self.scripts[k] = v

    def __getitem__(self, k):
        return self.scripts[k]

    def __delitem__(self, k):
        if self.active == k:
            raise ValueError('Script is active')
        del self.scripts[k]

    def __iter__(self):
        for k in self.scripts:
            yield k

    def has_key(self, k):
        return self.scripts.has_key(k)

    def is_active(self, k):
        return self.active == k

    def set_active(self, k):
        if k != None and k not in self.scripts:
            raise KeyError('Unknown script')
        self.active = k


class new(__init__.new):
    def init(self, config):
        self.warn = config.getboolean('Accept', 'warn', True)

    def auth(self, params):
        if self.warn:
            warnings.warn('The "accept" module is for testing only!')
        return True

    def lookup(self, params):
        if self.warn:
            warnings.warn('The "accept" module is for testing only!')
        return '/tmp'

    def create_storage(self, params):
        if self.warn:
            warnings.warn('The "accept" module is for testing only!')
        return ScriptStorage()
