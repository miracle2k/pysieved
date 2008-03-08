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
import syslog
import sys
from config import Config
try:
    from tlslite.api import *
    have_tls = True
except:
    have_tls = False


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
    parser.add_option('-b', '--bindaddr',
                      help='What IP address to bind to (default all)',
                      action='store', dest='bindaddr', default=None)
    parser.add_option('-p', '--pidfile',
                      help='Where to write a PID file',
                      action='store', dest='pidfile', default=None)
    parser.add_option('-c', '--config',
                      help='Location of config file',
                      action='store', dest='config',
                      default='/usr/local/etc/pysieved.ini')
    parser.add_option('-v', '--verbosity',
                      help="Set logging verbosity level (default 1)",
                      action='store', dest='verbosity', default=1, type='int')
    parser.add_option('-d', '--debug',
                      help='Log to stderr',
                      action='store_true', dest='debug', default=False)
    parser.add_option('-B', '--base',
                      help='Mail base directory',
                      action='store', dest='base', default='')
    parser.add_option('-T', '--tls',
                      help='STARTTLS required before authentication',
                      action='store', dest='tls_required', default=False)
    parser.add_option('-K', '--key',
                      help='TLS private key file',
                      action='store', dest='tls_key', default='')
    parser.add_option('-C', '--cert',
                      help='TLS certificate file',
                      action='store', dest='tls_cert', default='')
    (options, args) = parser.parse_args()

    # Read config file
    config = Config(options.config)

    port = options.port or config.getint('main', 'port', 2000)
    addr = options.bindaddr or config.get('main', 'bindaddr', '')
    pidfile = options.pidfile or config.get('main', 'pidfile',
                                            '/var/run/pysieved.pid')
    base = options.base or config.get('main', 'base', '')
    tls_required = options.tls_required or config.getboolean('TLS', 'required', False)
    tls_key = options.tls_key or config.get('TLS', 'key', '')
    tls_cert = options.tls_cert or config.get('TLS', 'cert', '')


    # Load TLS key and cert
    if have_tls and tls_key and tls_cert:
        try:
            tls_read_cert = open(tls_cert).read()
            tls_x509 = X509()
            tls_x509.parse(tls_read_cert)
            tls_certChain = X509CertChain([tls_x509])
            tls_read_key = open(tls_key).read()
            tls_privateKey = parsePEMKey(tls_read_key, private=True)
        except:
            tls_required = False
            tls_privateKey = None
            tls_certChain = None
    else:
        tls_required = False
        tls_privateKey = None
        tls_certChain = None


    ##
    ## Import plugins
    ##
    auth = __import__('plugins.%s' % config.get('main', 'auth', 'SASL').lower(),
                      None, None, True)
    userdb = __import__('plugins.%s' % config.get('main', 'userdb', 'passwd').lower(),
                      None, None, True)
    storage = __import__('plugins.%s' % config.get('main', 'storage', 'Dovecot').lower(),
                         None, None, True)


    # Define the log function
    syslog.openlog('pysieved[%d]' % (os.getpid()), 0, syslog.LOG_MAIL)
    def log(l, s):
        if l <= options.verbosity:
            if options.debug:
                sys.stderr.write('%s %s\n' % ("=" * l, s))
            else:
                if l > 0:
                    lvl = syslog.LOG_NOTICE
                elif l == 0:
                    lvl = syslog.LOG_WARNING
                else:
                    lvl = syslog.LOG_ERR
                syslog.syslog(lvl, s)


    # If the same plugin is used in two places, recycle it
    authenticate = auth.new(log, config)

    if userdb == auth:
        homedir = authenticate
    else:
        homedir = userdb.new(log, config)

    if storage == auth:
        store = authenticate
    elif storage == userdb:
        store = homedir
    else:
        store = storage.new(log, config)


    class handler(managesieve.RequestHandler):
        capabilities = store.capabilities

        def __init__(self, *args):
            self.params = {}
            managesieve.RequestHandler.__init__(self, *args)

        def log(self, l, s):
            log(l, s)

        def list_mech(self):
            mechs = authenticate.mechanisms()
            self.log(5, "Announcing mechanisms : %r" % mechs)
            return mechs

        def do_sasl_first(self, mechanism, *args):
            self.log(5, "Starting SASL authentication (%s) : %s" % (mechanism, ' '.join(args)))
            ret = authenticate.do_sasl_first(mechanism, *args);
            if ret['result'] == 'CONT':
                self.log(5, "Need more SASL authentication : %r" % ret)
            else:
                self.log(5, "Finished SASL authentication : %r" % ret)
            return ret

        def do_sasl_next(self, b64_string):
            self.log(5, "Continuing SASL authentication : %s" % b64_string)
            ret = authenticate.do_sasl_next(b64_string);
            if ret['result'] == 'CONT':
                self.log(5, "Need more SASL authentication : %r" % ret)
            else:
                self.log(5, "Finished SASL authentication : %r" % ret)
            return ret

        def authenticate(self, username, passwd):
            self.log(5, "Authenticating %s" % username)
            self.params['username'] = username
            self.params['password'] = passwd
            return authenticate.auth(self.params)

        def get_homedir(self, username):
            self.params['username'] = username
            ret = homedir.lookup(self.params)
            self.log(5, "Plugin returned home : %r" % ret)
            if ret and not os.path.isabs(ret) and base:
                ret = os.path.join(base, ret)
                self.log(5, "Added base to home : %r" % ret)
            return ret

        def new_storage(self, homedir):
            self.params['homedir'] = homedir
            return store.create_storage(self.params)

        def get_tls_params(self):
            return {'required': tls_required,
                    'key': tls_privateKey,
                    'cert': tls_certChain}

    if options.stdin:
        sock = socket.fromfd(0, socket.AF_INET, socket.SOCK_STREAM)
        h = handler(sock, sock.getpeername(), None)
    else:
        import daemon

        s = Server((addr, port), handler)

        if not options.debug:
            daemon.daemon(pidfile=pidfile)
        log(1, 'Listening on %s port %d' % (addr or "INADDR_ANY", port))
        s.serve_forever()

if __name__ == '__main__':
    main()
