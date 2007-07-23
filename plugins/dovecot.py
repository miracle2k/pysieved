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
import socket
import base64
import os
import popen2





####################################
## Storage stuff


def quote(str):
    return urllib.quote(str, '')

def unquote(str):
    return urllib.unquote(str)


def write_out(sievec, basedir, final, txt):
    script = TempFile(basedir)
    compiled = TempFile(basedir)

    compiled.close()
    script.write(txt)
    script.close()

    p = popen2.Popen3(('%s %s %s ' % (sievec,
                                      script.name,
                                      compiled.name)),
                      True)
    p.tochild.close()
    ret_str = p.fromchild.read().strip()
    err_str = p.childerr.read().strip()
    p.fromchild.close()
    p.childerr.close()
    if p.wait():
        raise ValueError(err_str)
    os.rename(script.name, final)


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


class ScriptStorage(__init__.ScriptStorage):
    def __init__(self, sievec, mydir, homedir):
        self.sievec = sievec
        self.mydir = mydir
        self.homedir = homedir
        self.basedir = os.path.join(self.homedir, self.mydir)
        self.active = os.path.join(self.homedir, '.dovecot.sieve')

        # Create our directory if needed
        if not os.path.exists(self.basedir):
            os.mkdir(self.basedir)

        # If they already have a script, shuffle it into where we want it
        if os.path.exists(self.active) and not os.path.islink(self.active):
            os.rename(self.active, os.path.join(self.basedir, 'dovecot'))
            self.set_active('dovecot')


    def __setitem__(self, k, v):
        write_out(self.sievec,
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



class new(__init__.new):
    capabilities = ('fileinto reject envelope vacation imapflags '
                    'notify subaddress relational '
                    'comparator-i;ascii-numeric')

    def init(self, config):
        self.mux = config.get('Dovecot', 'mux', False)
        self.master = config.get('Dovecot', 'master', False)
        self.service = config.get('Dovecot', 'service', 'pysieved')
        self.sievec = config.get('Dovecot', 'sievec',
                                 '/usr/lib/dovecot/sievec')
        self.scripts_dir = config.get('Dovecot', 'scripts', '.pysieved')
        self.uid = config.getint('Dovecot', 'uid', None)
        self.gid = config.getint('Dovecot', 'gid', None)

        # Drop privileges here if all users share the same uid/gid
        if self.gid >= 0:
            os.setgid(self.gid)
        if self.uid >= 0:
            os.setuid(self.uid)


    def auth(self, params):
        # We can do this only if a MUX socket was specified
        if self.mux:
            self.auth_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.auth_sock.connect(self.mux)
            handshake_string = self.auth_sock.recv(1024)
            self.auth_sock.sendall('VERSION\t1\t0\nCPID\t%d\n' % os.getpid())
        else:
            raise ValueError('No MUX socket was specified')

        # Since this socket will be used only once, use a hardcoded request ID
        auth_string = ('AUTH\t%d\tPLAIN\tservice=%s\tresp=%s' %
                       (1,
                        self.service,
                        base64.encodestring(params['username'] + '\0' +
                                            params['username'] + '\0' +
                                            params['password'])))
        self.auth_sock.sendall(auth_string + '\n')
        ret = self.auth_sock.recv(1024)

        self.auth_sock.close();

        if ret.startswith('OK'):
            return True
        return False


    def lookup(self, params):
        # We can do this only if a master socket was specified
        if self.master:
            self.user_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.user_sock.connect(self.master)
            master_handshake_string = self.user_sock.recv(1024)
            self.user_sock.sendall('VERSION\t1\t0\n')
        else:
            raise ValueError('No master socket was specified')

        # Since this socket will be used only once, use a hardcoded request ID
        lookup_string = ('USER\t%d\t%s\tservice=%s' %
                         (1,
                          params['username'],
                          self.service))
        self.user_sock.sendall(lookup_string + '\n')
        ret = self.user_sock.recv(1024)

        self.user_sock.close();

        if ret.startswith('USER\t'):
            uid = ret[ret.find('\tuid=')+5:]
            uid = uid[:uid.find('\t')]
            gid = ret[ret.find('\tgid=')+5:]
            gid = gid[:gid.find('\t')]
            home = ret[ret.find('\thome=')+6:]
            home = home[:home.find('\t')]

            # Assuming we were started with elevated privileges, drop them now
            if (self.gid < 0) and (int(gid) >= 0):
                os.setgid(int(gid))

            if (self.uid < 0) and (int(uid) >= 0):
                os.setuid(int(uid))

            return home
        else:
            return None


    def create_storage(self, params):
        return ScriptStorage(self.sievec,
                             self.scripts_dir,
                             params['homedir'])
