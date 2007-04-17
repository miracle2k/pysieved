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
import tempfile
import stat
import os
import popen2
import dovecot


class ScriptStorage(__init__.ScriptStorage):
    """Script storage where you only get one script.

    A dumbed-down version of the dovecot storage class.

    """


    def __init__(self, sievec, homedir, scriptname):
        self.sievec = sievec
        self.homedir = homedir
        self.scriptname = scriptname
        self.active = os.path.join(self.homedir, '.dovecot.sieve')


    def __setitem__(self, k, v):
        if k != self.scriptname:
            raise KeyError('Unknown script')
        dovecot.write_out(self.sievec, self.homedir, self.active, v)


    def __getitem__(self, k):
        if k != self.scriptname:
            raise KeyError('Unknown script')
        try:
            return file(self.active).read()
        except IOError:
            raise KeyError('Unknown script')


    def __delitem__(self, k):
        # Unfortunately there's no way to deactivate anything, so we can't
        # do any checks to prevent deleting an active script.
        if k != self.scriptname:
            raise KeyError('Unknown script')
        try:
            os.unlink(self.active)
        except OSError:
            raise KeyError('Unknown script')


    def __iter__(self):
        yield self.scriptname


    def has_key(self, k):
        if k != self.scriptname:
            return False
        return os.path.exists(self.active)


    def is_active(self, k):
        return self.has_key(k)


    def set_active(self, k):
        if not self.has_key(k):
            raise KeyError('Unknown script')


class new(dovecot.new):
    def init(self, config):
        dovecot.new.init(self, config)
        self.scriptname = config.get('Dovecot Single', 'scriptname', 'phpscript')


    def create(self, homedir):
        return ScriptStorage(self.sievec, homedir, self.scriptname)

