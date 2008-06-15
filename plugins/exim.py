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
import FileStorage
import socket
import os
import popen2
import re


class EximStorage(FileStorage.FileStorage):
    def __init__(self, sieve_test, mydir, active_file, homedir):
        self.sieve_test = sieve_test
        self.mydir = mydir
        self.active_file = active_file
        self.homedir = homedir
        self.basedir = os.path.join(self.homedir, self.mydir)
        self.active = os.path.join(self.homedir, self.active_file)
        self.sieve_hdr = '# Sieve filter'
        self.sieve_re = re.compile('^' + re.escape(self.sieve_hdr))

        # Create our directory if needed
        if not os.path.exists(self.basedir):
            os.mkdir(self.basedir)

        # If they already have a script, shuffle it into where we want it
        if os.path.exists(self.active) and not os.path.islink(self.active):
            try:
                # Make sure this is an Exim Sieve filter
                script = file(self.active).read()
                if re.match(self.sieve_re, script, re.S):
                    os.rename(self.active, os.path.join(self.basedir, 'exim'))
                    self.set_active('exim')
            except IOError:
                pass


    def __setitem__(self, k, v):
        if not re.match(self.sieve_re, v, re.S):
            v = self.sieve_hdr + '\n' + v
        FileStorage.FileStorage.__setitem__(self, k, v)


class PysievedPlugin(__init__.PysievedPlugin):
    capabilities = ('envelope fileinto encoded-character '
                    'enotify subaddress vacation copy '
                    'comparator-i;ascii-casemap comparator-en;ascii-casemap '
                    'comparator-i;octet comparator-i;ascii-numeric')

    def init(self, config):
        self.sendmail = config.get('Exim', 'sendmail',
                                 '/usr/sbin/sendmail')
        self.scripts_dir = config.get('Exim', 'scripts', '.pysieved')
        self.active_file = config.get('Exim', 'active', '.forward')
        self.uid = config.getint('Exim', 'uid', -1)
        self.gid = config.getint('Exim', 'gid', -1)

        # Drop privileges here if all users share the same uid/gid
        if self.gid >= 0:
            os.setgid(self.gid)
        if self.uid >= 0:
            os.setuid(self.uid)


    def exim_test(self, basedir, script):
        compiled = FileStorage.TempFile(basedir)
        compiled.close()
        p = popen2.Popen3(('%s -bf %s < %s' % (self.sendmail,
                                               script,
                                               '/dev/null')),
                          True)
        p.tochild.close()
        ret_str = p.fromchild.read().strip()
        err_str = p.childerr.read().strip()
        p.fromchild.close()
        p.childerr.close()
        if p.wait():
            return False
        return True


    def create_storage(self, params):
        return EximStorage(self.exim_test,
                           self.scripts_dir,
                           self.active_file,
                           params['homedir'])
