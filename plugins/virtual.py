#! /usr/bin/python

import __init__
import os

class new(__init__.new):
    def init(self, config):
        self.uid = config.getint('Virtual', 'uid', None)
        self.gid = config.getint('Virtual', 'gid', None)
        self.base = config.get('Virtual', 'base', None)
        self.hostdirs = config.getboolean('Virtual', 'hostdirs', False)
        assert (self.uid and self.gid and self.base)

    def lookup(self, params):
        username = params['username']
        if self.hostdirs:
            parts = username.split('@', 1)
            username = os.path.join(parts[1], parts[0])
        if self.gid >= 0:
            os.setgid(self.gid)
        if self.uid >= 0:
            os.setuid(self.uid)
        return os.path.join(self.base, username)
