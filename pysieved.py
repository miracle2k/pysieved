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

import optparse
import SocketServer
import socket
import os
import managesieve
from config import Config


class Server(SocketServer.ForkingTCPServer):
    allow_reuse_address = True


def main():
    parser = optparse.OptionParser()
    parser.add_option('-i', '--inetd',
                      help='Run once on stdin (inetd mode)',
                      action='store_true', dest='stdin', default=False)
    parser.add_option('-l', '--port',
                      help='What port to run on (default 2000)',
                      action='store', dest='port', default=None, type='int')
    parser.add_option('-p', '--pidfile',
                      help='Where to write a PID file',
                      action='store', dest='pidfile', default=None)
    parser.add_option('-c', '--config',
                      help='Location of config file',
                      action='store', dest='config',
                      default='/usr/local/etc/pysieved.ini')
    parser.add_option('-d', '--debug',
                      help='Turn on debugging (twice for more verbosity)',
                      action='count', dest='debug')
    (options, args) = parser.parse_args()

    # Read config file
    config = Config(options.config)

    port = options.port or config.getint('main', 'port', 2000)
    pidfile = options.pidfile or config.get('main', 'pidfile',
                                            '/var/run/pysieved.pid')
    auth = __import__('auth.%s' % config.get('main', 'auth', 'SASL').lower(),
                      None, None, True)
    userdb = __import__('userdb.%s' % config.get('main', 'userdb', 'passwd').lower(),
                      None, None, True)
    storage = __import__('storage.%s' % config.get('main', 'storage', 'Dovecot').lower(),
                         None, None, True)


    authenticate = auth.new(options.debug, config)
    homedir = userdb.new(options.debug, config)
    store = storage.new(options.debug, config)

    class handler(managesieve.RequestHandler):
        debug = options.debug
        capabilities = store.capabilities

        def authenticate(self, username, passwd):
            return authenticate.auth(username, passwd)

        def get_homedir(self, username):
            return homedir.lookup(username)

        def new_storage(self, homedir):
            return store.create(homedir)

    if options.stdin:
        sock = socket.fromfd(0, socket.AF_INET, socket.SOCK_STREAM)
        h = handler(sock, sock.getpeername(), None)
    else:
        import daemon

        s = Server(('', port), handler)

        if not options.debug:
            daemon.daemon(pidfile=pidfile)
        s.serve_forever()

if __name__ == '__main__':
    main()
