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


import plugins.accept
import managesieve
import unittest
import thread
import Queue
import time
import socket
import tempfile
import config

version = managesieve.version

class DebugRequestHandler(managesieve.RequestHandler):
    capabilities = 'fileinto vacation'

    def do_debug(self, *args):
        """Special function for big fat cheaters like the test suite."""

        if args:
            arg = args[0]
        else:
            arg = None
        reason = 'You are a big fat cheater'
        if arg == 'tls':
            self.tls = True
            reason = 'You are a big fat cheater'
        elif arg == 'ping':
            reason = 'PONG'
        elif arg == 'echo':
            for a in args[1:]:
                self.send(a)
            reason = None
        else:
            self.send('tls', `self.tls`)
            self.send('user', `self.user`)
            reason = None
        self.ok(reason=reason)

    def authenticate(self, user, passwd):
        return True

    def get_homedir(self, user):
        return None

    def new_storage(self, homedir):
        return plugins.accept.ScriptStorage()


class StringSock:
    """Dupes the testee into thinking it has a real socket"""

    def __init__(self):
        self.output = Queue.Queue()
        self.input = Queue.Queue()
        self.connected = True

    ##
    ## This can be used by anybody
    ##
    def close(self):
        self.connected = False
        self.input.put('')
        self.output.put('')

    ##
    ## These are used by the part of the program being duped
    ##
    def send(self, dat):
        self.output.put(dat)

    def recv(self, n):
        if not self.connected:
            return ''
        return self.input.get()

    ##
    ## These are used by the test code
    ##
    def push(self, dat):
        self.input.put(dat)

    def expect(self, dat):
        assert self.connected, 'Not connected'
        d = self.output.get(timeout=1)
        assert d==dat, ('%r != %r' % (d, dat))


class Basic(unittest.TestCase):
    def setUp(self):
        self.sock = StringSock()
        thread.start_new(DebugRequestHandler,
                         (self.sock, None, None))
        self.expect('"IMPLEMENTATION" "%s"\r\n' % version)
        self.expect('"SASL" "PLAIN"\r\n')
        self.expect('"SIEVE" "fileinto vacation"\r\n')
        self.expect('OK\r\n')

    def tearDown(self):
        self.sock.close()
        self.failIf(self.sock.connected, "Still connected")

    def push(self, txt):
        return self.sock.push(txt)

    def expect(self, txt):
        return self.sock.expect(txt)


class Unauthenticated(Basic):
    def testParser(self):
        self.push('debug echo 1\r\n')
        self.expect('"1"\r\n')
        self.expect('OK\r\n')

        self.push('debug echo ""\r\n')
        self.expect('""\r\n')
        self.expect('OK\r\n')

        self.push('debug echo {3+}\r\nhi!\r\n')
        self.expect('"hi!"\r\n')
        self.expect('OK\r\n')

        self.push('debug echo "sandwich"\r\n')
        self.expect('"sandwich"\r\n')
        self.expect('OK\r\n')

    def testUnknown(self):
        self.push('ooga\r\n')
        self.expect('NO "Unknown command"\r\n')

    def testArgs(self):
        self.push('capability foo\r\n')
        self.expect('NO "Wrong number of arguments"\r\n')
        self.push('havespace foo\r\n')
        self.expect('NO "Wrong number of arguments"\r\n')

    def testFakeTLS(self):
        self.push('debug tls\r\n')
        self.expect('OK "You are a big fat cheater"\r\n')
        self.push('capability\r\n')
        self.expect('"IMPLEMENTATION" "%s"\r\n' % version)
        self.expect('"SASL" "PLAIN"\r\n')
        self.expect('"SIEVE" "fileinto vacation"\r\n')
        self.expect('OK\r\n')

    def testAuthNoTLS(self):
        return
        self.push('authenticate plain snot\r\n')
        self.expect('NO (ENCRYPT-NEEDED)\r\n')

    def testCurlyBracePlusWeirdness(self):
        self.push('debug {4+}\r\nping\r\n')
        self.expect('OK "PONG"\r\n')
        self.push('debug {4+}\r\n')
        self.push('ping\r\n')
        self.expect('OK "PONG"\r\n')

    def testUnauth(self):
        self.push('havespace "whatever" 1\r\n')
        self.expect('NO "Authenticate first"\r\n')
        self.push('putscript "whatever" "whatever"\r\n')
        self.expect('NO "Authenticate first"\r\n')
        self.push('listscripts\r\n')
        self.expect('NO "Authenticate first"\r\n')
        self.push('setactive "whatever"\r\n')
        self.expect('NO "Authenticate first"\r\n')
        self.push('getscript "whatever"\r\n')
        self.expect('NO "Authenticate first"\r\n')
        self.push('deletescript "whatever"\r\n')
        self.expect('NO "Authenticate first"\r\n')


class Authenticated(Basic):
    def setUp(self):
        Basic.setUp(self)
        self.push('debug tls\r\n')
        self.expect('OK "You are a big fat cheater"\r\n')
        cred = 'fred\0fred\0secret'.encode('base64')
        self.push('authenticate plain "%s"\r\n' % cred)
        self.expect('OK\r\n')


    def testHavespace(self):
        self.push('havespace goob 10000000000\r\n')
        self.expect('NO (QUOTA) "Quota exceeded"\r\n')
        self.push('havespace goob 1\r\n')
        self.expect('OK\r\n')
        self.push('havespace goob fred\r\n')
        self.expect('NO "Not a number"\r\n')


    def testAddRemove(self):
        self.push('putscript a "Script A"\r\n')
        self.expect('OK\r\n')

        self.push('getscript a\r\n')
        self.expect('{8+}\r\n')
        self.expect('Script A\r\n')
        self.expect('OK\r\n')

        self.push('listscripts\r\n')
        self.expect('"a"\r\n')
        self.expect('OK\r\n')

        self.push('setactive a\r\n')
        self.expect('OK\r\n')

        self.push('listscripts\r\n')
        self.expect('"a" ACTIVE\r\n')
        self.expect('OK\r\n')

        self.push('deletescript a\r\n')
        self.expect('NO "Script is active"\r\n')

        self.push('setactive ""\r\n')
        self.expect('OK\r\n')

        self.push('listscripts\r\n')
        self.expect('"a"\r\n')
        self.expect('OK\r\n')

        self.push('deletescript a\r\n')
        self.expect('OK\r\n')


    def testNoScript(self):
        self.push('setactive a\r\n')
        self.expect('NO "No script by that name"\r\n')

        self.push('deletescript a\r\n')
        self.expect('NO "No script by that name"\r\n')

        self.push('getscript a\r\n')
        self.expect('NO "No script by that name"\r\n')

        self.push('listscripts\r\n')
        self.expect('OK\r\n')


class ConfigParser(unittest.TestCase):
    """Test the config file parser"""

    def setUp(self):
        self.f = tempfile.NamedTemporaryFile()

    def testJunk(self):
        self.f.write('[main]\n')
        self.f.write('foo = bar\n')
        self.f.write('int = 1\n')
        self.f.write('boo = on\n')
        self.f.flush()
        c = config.Config(self.f.name)
        self.failUnlessEqual(c.get('main', 'foo', 'baz'), 'bar')
        self.failUnlessEqual(c.get('main', 'arf', 'baz'), 'baz')
        self.failUnlessEqual(c.getint('main', 'int', 3), 1)
        self.failUnlessEqual(c.getint('main', 'iao', 3), 3)
        self.failUnlessEqual(c.getboolean('main', 'boo'), True)


class RegressionInetd(unittest.TestCase):
    """Regression test the whole program"""

    def setUp(self):
        from plugins import dovecot

        self.buf = ''

        sockname = '/tmp/unittest.%d' % os.getpid()

        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.bind(sockname)
        s.listen(1)

        self.pid = os.fork()
        if self.pid:
            # Server
            self.c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.c.connect(sockname)
        else:
            # Client
            c, _ = s.accept()
            del s
            os.dup2(c.fileno(), 0)
            argv = 'python pysieved.py --inetd --debug'.split(' ')
            if os.getuid() != 0:
                argv[:0] = ['sudo']
            os.execlp(argv[0], *argv)

        os.unlink(sockname)
        self.expect('"IMPLEMENTATION" "%s"\r\n' % version)
        self.expect('"SASL" "PLAIN"\r\n')
        self.expect('"SIEVE" "%s"\r\n' % dovecot.new.capabilities)
        self.expect('OK\r\n')

        # Log in
        self.user, self.passwd = os.environ['TEST_AUTH'].split(':', 1)

        auth = ('%s\0%s\0%s' % (self.user, self.user, self.passwd)).encode('base64').strip()
        self.push('authenticate "plain" "%s"\r\n' % (auth))
        self.expect('OK\r\n')


    def tearDown(self):
        os.kill(self.pid, 9)
        os.wait()

    def write(self, dat):
        return self.c.send(dat)

    def read(self, n):
        return self.c.recv(n)


    def expect(self, dat):
        while (not self.buf) or (len(self.buf) < len(dat)):
            self.buf += self.read(1000)
        if self.buf.startswith(dat):
            self.buf = self.buf[len(dat):]
        else:
            raise AssertionError('%r != %r' % (self.buf, dat))

    def push(self, dat):
        self.write(dat)

    def testOne(self):
        name = 'unittest %d' % (os.getpid())
        self.write('putscript "%s" {9+}\r\nfrobozz;\n\r\n' % name)
        self.expect('NO "Info: line 1: syntax error"\r\n')

        self.write('putscript "%s" ""\r\n' % name)
        self.expect('OK\r\n')

        script = ('if address :is "to" "fred@example.com"\n'
                  '{\n'
                  '  redirect "barney@example.org";\n'
                  '}\n')
        self.write('putscript "%s" {%d+}\r\n' % (name, len(script)))
        self.write('%s\r\n' % script)
        self.expect('OK\r\n')

        self.write('getscript "%s"\r\n' % name)
        self.expect('{%d+}\r\n%s\r\n' % (len(script), script))
        self.expect('OK\r\n')

        self.write('deletescript "%s"\r\n' % name)
        self.expect('OK\r\n')


class RegressionDaemon(unittest.TestCase):
    def setUp(self):
        import random
	import time

        f = tempfile.NamedTemporaryFile()
	self.port = random.randint(3000, 6000)
	ret = os.system('python pysieved.py -l %d -p %s' % (self.port, f.name))
	self.failIf(ret)
	time.sleep(0.1)
	f.seek(0)
	self.pid = int(f.read())


    def tearDown(self):
        os.kill(self.pid, 9)


    def testOne(self):
        from plugins import dovecot
        import socket
	import time

	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect(('127.0.0.1', self.port))
	time.sleep(0.1)
	d = s.recv(4000)
	self.failUnlessEqual(d, ('"IMPLEMENTATION" "%s"\r\n'
                                 '"SASL" "PLAIN"\r\n'
                                 '"SIEVE" "%s"\r\n'
                                 'OK\r\n' % (version,
                                             dovecot.new.capabilities)))



if __name__ == '__main__':
    from plugins.test import *

    unittest.main()
