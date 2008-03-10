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
import urllib
import tempfile
import stat
import os





####################################
## Storage stuff


def quote(str):
    return urllib.quote(str, '')

def unquote(str):
    return urllib.unquote(str)


def write_out(sieve_test, basedir, final, txt):
    script = TempFile(basedir)

    script.write(txt)
    script.close()

    if sieve_test(basedir, script.name):
        os.rename(script.name, final)
    else:
        raise ValueError()


class TempFile:
    """Like NamedTemporaryFile but won't complain if unlink fails"""

    def __init__(self, dir):
        fd, self.name = tempfile.mkstemp(dir=dir)
        self.file = os.fdopen(fd, 'w+b')
        self.unlink = os.unlink

    def __getattr__(self, name):
        return getattr(self.file, name)

    def close(self):
        if not self.file:
            return
        self.file.close()
        self.file = None

    def __del__(self):
        self.close()
        try:
            self.unlink(self.name)
        except OSError:
            pass


class FileStorage(__init__.ScriptStorage):
    def __init__(self, sieve_test, mydir, active_file, homedir):
        self.sieve_test = sieve_test
        self.mydir = mydir
        self.active_file = active_file
        self.homedir = homedir
        self.basedir = os.path.join(self.homedir, self.mydir)
        self.active = os.path.join(self.homedir, self.active_file)

        # Create our directory if needed
        if not os.path.exists(self.basedir):
            os.mkdir(self.basedir)

        # If they already have a script, shuffle it into where we want it
        if os.path.exists(self.active) and not os.path.islink(self.active):
            os.rename(self.active, os.path.join(self.basedir, 'dovecot'))
            self.set_active('dovecot')


    def __setitem__(self, k, v):
        write_out(self.sieve_test,
                  self.basedir,
                  os.path.join(self.basedir, quote(k)),
                  v)


    def __getitem__(self, k):
        fn = os.path.join(self.basedir, quote(k))
        try:
            return file(fn).read()
        except IOError:
            raise KeyError('Unknown script')


    def __delitem__(self, k):
        if k and self.is_active(k):
            raise ValueError('Script is active')
        fn = os.path.join(self.basedir, quote(k))
        try:
            os.unlink(fn)
        except OSError:
            raise KeyError('Unknown script')


    def __iter__(self):
        for s in os.listdir(self.basedir):
            if s[0] == '.':
                continue
            if s[-1] == '~':
                continue
            yield unquote(s)


    def has_key(self, k):
        fn = os.path.join(self.basedir, quote(k))
        return os.path.exists(fn)


    def is_active(self, k):
        fn = os.path.join(self.basedir, quote(k))
        if not self.has_key(k):
            raise KeyError('Unknown script %s' % k)
        try:
            return os.path.samefile(fn, self.active)
        except OSError:
            return False


    def set_active(self, k):
        if k:
            fn = os.path.join(self.mydir, quote(k))
            if not self.has_key(k):
                raise KeyError('Unknown script')
        try:
            os.unlink(self.active)
        except OSError:
            pass
        if k:
            os.symlink(fn, self.active)



