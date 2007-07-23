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
import socket
import struct


def pack(s):
    return struct.pack('!H', len(s)) + s


class new(__init__.new):
    def init(self, config):
        self.mux = config.get('SASL', 'mux', '/var/run/saslauthd/mux')
        self.service = config.get('SASL', 'service', 'pysieved')

    def sasl(self, *args):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(self.mux)
        s.send(''.join([pack(x) for x in args]))
        r = s.recv(2)
        (n,) = struct.unpack('!H', r)
        return s.recv(n)

    def auth(self, params):
        ret = self.sasl(params['username'],
                        params['password'],
                        self.service,
                        '')
        self.log(2, 'Auth returns %r' % ret)
        if ret.startswith('OK'):
            return True
        return False


if __name__ == '__main__':
    import sys

    class C:
        def get(self, section, key, default):
            return default

    n = new(C())
    print n.auth({'username': sys.argv[1],
                  'password': sys.argv[2]})
