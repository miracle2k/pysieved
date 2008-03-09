#! /usr/bin/env python

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

import SocketServer
import socket
import time
import os
import sys
try:
    from tlslite.api import *
    have_tls = True
except:
    have_tls = False

version = "pysieved 0.91+DEV"
maxsize = 100000


def compact_traceback():
    """Return a compact (1-line) traceback.

    Lifted from asyncore.py from the Python 2.4 distribution.

    """

    t, v, tb = sys.exc_info()
    tbinfo = []
    assert tb # Must have a traceback
    while tb:
        tbinfo.append((
            tb.tb_frame.f_code.co_filename,
            tb.tb_frame.f_code.co_name,
            str(tb.tb_lineno)
            ))
        tb = tb.tb_next

    # just to be safe
    del tb

    file, function, line = tbinfo[-1]
    info = ' '.join(['[%s|%s|%s]' % x for x in tbinfo])
    return (file, function, line), t, v, info


class Hangup(Exception):
    pass


class AuthenticateFirst(Exception):
    pass



class RequestHandler(SocketServer.BaseRequestHandler):
    def __init__(self, request, client_address, server):
        self.user = None
        self.storage = None
        self.tls = None
        self.tls_params = self.get_tls_params()
        SocketServer.BaseRequestHandler.__init__(self,
                                                 request,
                                                 client_address,
                                                 server)

    def log(self, l, s):
        print time.time(), "=" * l, s


    def send(self, *args):
        out = []
        def flush(out):
            s = ' '.join(out) + '\r\n'
            self.log(3, 'S: %r' % s)
            self.write(s)
            del out[:]

        for a in args:
            if type(a) == type(()):
                out.append(' '.join(a))
            elif len(a) > 200 or '"' in a:
                out.append('{%d}' % len(a))
                flush(out)
                self.log(3, 'S: %r' % a)
                self.write(a)
            else:
                out.append('"%s"' % a)
        flush(out)


    def _rsp(self, rsp, code, reason):
        out = rsp
        if code:
            out += ' (%s)' % code
        if reason:
            out += ' "%s"' % reason
        out += '\r\n'
        self.log(3, 'S: %r' % out)
        self.write(out)


    def ok(self, code=None, reason=None):
        self._rsp('OK', code, reason)


    def no(self, code=None, reason=None):
        self._rsp('NO', code, reason)


    def bye(self, code=None, reason=None):
        self._rsp('BYE', code, reason)


    def bread(self, n):
        out = self.buf
        while len(out) < n:
            r = self.read(n - len(out))
            if not r:
                raise Hangup()
            out += r
        self.buf = out[n:]

        s = out[:n]
        self.log(3, 'C: %r' % s)
        return s


    def readline(self):
        out = self.buf
        while True:
            pos = out.find('\r\n')
            if pos > -1:
                self.buf = out[pos+2:]
                s = out[:pos]
                self.log(3, 'C: %r' % (s + '\r\n'))
                return s
            r = self.read(1024)
            if not r:
                raise Hangup()
            out += r


    def handle(self):
        self.buf = ''
        self.write = lambda s: self.request.send(s)
        self.read = lambda n: self.request.recv(n)

        self.log(1, 'Connect from %r' % (self.client_address,))

        self.do_capability()
        try:
            while True:
                try:
                    cmd = self.get_command()
                except AssertionError, str:
                    self.no(reason=str)
                    continue

                try:
                    func = getattr(self, 'do_%s' % (cmd[0].lower()))
                except AttributeError:
                    self.no(reason='Unknown command')
                    continue

                try:
                    func(*cmd[1:])
                except AuthenticateFirst:
                    self.no(reason='Authenticate first')
                except TypeError, exc:
                    if exc.args[0].startswith('do_') and 'arguments' in exc.args[0]:
                        self.no(reason='Wrong number of arguments')
                        continue
                    else:
                        raise

        except Hangup:
            pass
        except:
            nil, t, v, tbinfo = compact_traceback()
            self.log(-1, '[ERROR] %s:%s %s' % (t, v, tbinfo))
            self.bye(reason='Server error')
            raise

    def finish(self):
        self.log(1, 'Disconnect')


    def get_command(self):
        oparts = ['']

        while True:
            s = self.readline()
            parts = s.split(' ')
            closed = True
            if not parts[0]:
                break

            for p in parts:
                if p[0] == '"':
                    closed = False
                    p = p[1:]
                if (p[-1] == '"' and
                    (len(p) == 1 or p[-2] != '\\')):
                    closed = True
                    p = p[:-1]
                elif not closed:
                    p += ' '
                p = p.replace('\\"', '"')
                oparts[-1] += p
                if closed:
                    oparts.append('')
            assert not oparts[-1], ('Misquoted argument', oparts)
            del oparts[-1]

            # Pull out {31+}-style parameters
            o = oparts[-1]
            if len(o) > 3 and o[0] == '{' and o[-2:] == '+}':
                try:
                    n = int(o[1:-2])
                except ValueError:
                    continue
                oparts[-1] = self.bread(n)
            else:
                break

        assert oparts != [''], 'No command given'
        return oparts


    def check_auth(self):
        "Fail if not authenticated"
        if not self.storage:
            raise AuthenticateFirst()


    def do_authenticate(self, mechanism, *args):
        "2.1.  AUTHENTICATE Command"

        assert not self.storage, 'Already authenticated'

        if self.tls_params['required'] and not self.tls:
            return self.no(code='ENCRYPT-NEEDED')

        # Handle initial exchange
        ret = self.do_sasl_first(mechanism, *args)

        while ret['result'] == 'CONT':
            # Server requests more data
            line = ('{%d}\r\n' % len(ret['msg']))
            self.log(3, 'S: %r' % line)
            self.write(line)
            line = ('%s\r\n' % ret['msg'])
            self.log(3, 'S: %r' % line)
            self.write(line)

            # Read client string
            s = self.readline()
            if len(s) > 3 and s[0] == '{' and s[-2:] == '+}':
                # Literal string
                try:
                    n = int(s[1:-2])
                except ValueError:
                    # Can't parse length
                    return self.no(reason='Malformed string literal')
                else:
                    s = self.bread(n)
                    # Data should be followed by CRLF
                    misc = self.readline()
                    if len(misc) > 0:
                        return self.no(reason='Malformed string literal')
            elif len(s) > 1 and s[0] == '"' and s[-1] == '"':
                # Quoted string
                s = s[1:-1]
            elif s == '*':
                # A single '*' cancels the exchange
                return self.no(reason='Authentication cancelled')
            else:
                # Neither literal nor quoted
                return self.no(reason='Malformed string')

            # Process client string
            ret = self.do_sasl_next(s)

        # Final result
        if ret['result'] == 'NO':
            return self.no(reason=ret['msg'])
        elif ret['result'] == 'BYE':
            self.bye(reason=ret['msg'])
            raise Hangup()

        # OK, get storage location for authorized user
        home = self.get_homedir(ret['username'])

        if not home:
            self.bye(reason='Server Error')
            raise Hangup()

        self.storage = self.new_storage(home)

        self.log(1, 'Authenticated user %s' % ret['username'])

        return self.ok()


    def do_starttls(self):
        "2.2.  STARTTLS Command"

        assert not self.storage, 'Already authenticated'
        assert have_tls, 'No TLS support'
        assert self.tls_params['key'], 'Undefined TLS private key'
        assert self.tls_params['cert'], 'Undefined TLS certificate'

        self.ok(reason='Begin TLS negotiation now')

        try:
            self.buf = ''
            self.tls = TLSConnection(self.request)
            self.tls.handshakeServer(certChain=self.tls_params['cert'],
                                     privateKey=self.tls_params['key'],
                                     reqCert=False)
            self.write = lambda s: self.tls.write(s)
            self.read = lambda n: self.tls.read(n)
            return self.do_capability()
        except:
            import traceback
            traceback.print_exc()


    def do_logout(self):
        "2.3.  LOGOUT Command"

        self.ok()
        raise Hangup()


    def do_capability(self):
        "2.4.  CAPABILITY Command"

        self.send('IMPLEMENTATION', version)
        if self.tls or not self.tls_params['required']:
            self.send('SASL', ' '.join(self.list_mech()))
        else:
            self.send('SASL')
        self.send('SIEVE', self.capabilities)
        if self.tls_params['key'] and self.tls_params['cert'] and not self.tls:
            self.send('STARTTLS')
        self.ok()


    def do_havespace(self, name, size):
        "2.5.  HAVESPACE Command"

        self.check_auth()
        try:
            s = int(size)
        except ValueError:
            return self.no(reason='Not a number')
        if int(size) < maxsize:
            return self.ok()
        else:
            return self.no(code='QUOTA', reason='Quota exceeded')


    def do_putscript(self, name, content):
        "2.6.  PUTSCRIPT Command"

        self.check_auth()
        try:
            self.storage[name] = content
        except ValueError, reason:
            return self.no(reason=reason)
        return self.ok()


    def do_listscripts(self):
        "2.7.  LISTSCRIPTS Command"

        self.check_auth()
        for i in self.storage:
            if self.storage.is_active(i):
                self.send(i, ('ACTIVE',))
            else:
                self.send(i)
        return self.ok()


    def do_setactive(self, name):
        "2.8.  SETACTIVE Command"

        self.check_auth()
        try:
            if not name:
                self.storage.set_active(None)
            else:
                self.storage.set_active(name)
        except KeyError:
            return self.no(reason='No script by that name')
        except:
            return self.no()
        return self.ok()


    def do_getscript(self, name):
        "2.9.  GETSCRIPT Command"

        self.check_auth()
        try:
            s = self.storage[name]
        except KeyError:
            return self.no(reason='No script by that name')
        line = ('{%d}\r\n' % len(s))
        self.log(3, 'S: %r' % line)
        self.write(line)
        line = ('%s\r\n' % s)
        self.log(3, 'S: %r' % line)
        self.write(line)
        return self.ok()


    def do_deletescript(self, name):
        "2.10.  DELETESCRIPT Command"

        self.check_auth()
        try:
            del self.storage[name]
        except ValueError:
            return self.no(reason='Script is active')
        except KeyError:
            return self.no(reason='No script by that name')
        return self.ok()

    def list_mech(self):
        raise NotImplementedError()

    def do_sasl_first(self, mechanism, *args):
        raise NotImplementedError()

    def do_sasl_next(self, b64_string):
        raise NotImplementedError()

    def authenticate(self, username, passwd):
        raise NotImplementedError()

    def get_homedir(self, username):
        raise NotImplementedError()

    def new_storage(self, homedir):
        raise NotImplementedError()

    def get_tls_params(self):
        return {'required': False,
                'key': None,
                'cert': None}



