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
    mechs = []
    version = [ 1, 0 ]

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

        # No sockets are open
        self.auth_sock = None
        self.user_sock = None


    def open_auth_socket(self):
        # The forked child should be short-lived enough that
        # it should be ok to open the authentication socket
        # only once

        # We can do this only if a MUX socket was specified
        if not self.mux:
            raise ValueError('No MUX socket was specified')

        # Open the socket
        self.log(7, 'Opening socket %s' % self.mux)
        self.auth_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.auth_sock.connect(self.mux)

        # Send our version and PID
        init_string = ('VERSION\t%d\t%d\nCPID\t%d\n' %
                       (self.version[0],
                        self.version[1],
                        os.getpid()))
        self.log(7, '> %r' % init_string)
        self.auth_sock.sendall(init_string)

        # Verify version
        greet = self.auth_sock.recv(1024)
        self.log(7, '< %r' % greet)
        if greet.find('VERSION\t%d\t' % self.version[0]) == -1:
            raise ValueError('Incompatible version number')

        # Grab mechanisms
        if len(self.mechs) == 0:
            for line in greet.splitlines():
                if line.startswith('MECH\t'):
                    parts = line.split('\t')
                    if parts[1].upper() not in [ mech.upper() for mech in self.mechs]:
                        self.log(7, 'Adding mechanism %s' % parts[1].upper())
                        self.mechs.append(parts[1].upper())

        # All done
        self.reqid = 0


    def mechanisms(self):
        # When first started, no mechanisms are known
        # Open the authentication and get a list from the daemon
        if len(self.mechs) == 0 and not self.auth_sock:
            self.open_auth_socket()

        return self.mechs


    def do_sasl_first(self, mechanism, *args):
        # Make sure the requested mechanism is supported
        if mechanism.upper() not in [ mech.upper() for mech in self.mechs ]:
            return {'result': 'NO',
                    'msg': 'Unsupported authentication mechanism'}

        # Build authentication request
        self.reqid = self.reqid + 1
        if len(args) > 0:
            auth_string = ('AUTH\t%d\t%s\tservice=%s\tresp=%s\n' %
                           (self.reqid,
                            mechanism.upper(),
                            self.service,
                            args[0]))
        else:
            auth_string = ('AUTH\t%d\t%s\tservice=%s\n' %
                           (self.reqid,
                            mechanism.upper(),
                            self.service))

        # We should already have a socket open, just perform the dialog
        return self.do_sasl_dialog(auth_string)


    def do_sasl_next(self, b64_string):
        # Build continuation request
        cont_string = ('CONT\t%d\t%s\n' %
                       (self.reqid,
                        b64_string))

        # We should already have a socket open, just perform the dialog
        return self.do_sasl_dialog(cont_string)


    def do_sasl_dialog(self, msg):
        # We should have an open socket by now
        if not self.auth_sock:
            return {'result': 'BYE', 'msg': 'Server Error'}

        # Dialog
        self.log(7, '> %r' % msg)
        self.auth_sock.sendall(msg)
        ret = self.auth_sock.recv(1024)
        self.log(7, '< %r' % ret)

        # Parse result
        if ret.startswith('OK'):
            pass
        elif ret.startswith('FAIL'):
            return {'result': 'NO', 'msg': 'Authentication failed'}
        elif ret.startswith('CONT\t'):
            ret = (ret.splitlines())[0]
            parts = ret.split('\t')
            if len(parts) >= 3:
                return {'result': 'CONT', 'msg': parts[2]}
            else:
                return {'result': 'CONT', 'msg': ''}
        else:
            return {'result': 'BYE', 'msg': 'Unexpected result'}

        # Extract the authorized user
        username = None

        ret = (ret.splitlines())[0]
        for part in ret.split('\t'):
            if part.startswith('user='):
                username = part[5:]

        return {'result': 'OK', 'username': username}


    def auth(self, params):
        # Refer to do_sasl_first
        ret = self.do_sasl_first('PLAIN',
                                 base64.encodestring('\0' +
                                                     params['username'] + '\0' +
                                                     params['password']))

        if ret['result'].startswith('OK'):
            return True
        return False


    def lookup(self, params):
        # We can do this only if a master socket was specified
        if not self.master:
            raise ValueError('No master socket was specified')

        if not self.user_sock:
            self.log(7, 'Opening socket %s' % self.master)
            self.user_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.user_sock.connect(self.master)
            init_string = ('VERSION\t%d\t%d\n' %
                           (self.version[0],
                           self.version[1]))
            self.log(7, '> %r' % init_string)
            self.user_sock.sendall(init_string)
            greet = self.user_sock.recv(1024)
            self.log(7, '< %r' % greet)
            if greet.find('VERSION\t%d\t' % self.version[0]) == -1:
                raise ValueError('Incompatible major version number')
            self.lookup_id = 0

        self.lookup_id = self.lookup_id + 1
        lookup_string = ('USER\t%d\t%s\tservice=%s\n' %
                         (self.lookup_id,
                          params['username'],
                          self.service))
        self.log(7, '> %r' % lookup_string)
        self.user_sock.sendall(lookup_string)
        ret = self.user_sock.recv(1024)
        self.log(7, '< %r' % ret)

        if ret.startswith('USER\t'):
            ret = (ret.splitlines())[0]

            uid = None
            gid = None
            home = None

            for part in ret.split('\t'):
              if part.startswith('uid='):
                  uid = part[4:]
              elif part.startswith('gid='):
                  gid = part[4:]
              elif part.startswith('home='):
                  home = part[5:]

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
