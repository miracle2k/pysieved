#! /usr/bin/python

import __init__
import os

class new(__init__.UserDB):
    def init(self, config):
        self.uid = config.getint('Virtual', 'uid', None)
        self.gid = config.getint('Virtual', 'gid', None)
        self.base = config.get('Virtual', 'base', None)
        self.atchar = config.get('Virtual', 'atchar', '/')
        assert (self.uid and self.gid and self.base)

    def lookup(self, username):
        username = username.replace('@', self.atchar)
        if self.gid >= 0:
            os.setgid(self.gid)
        if self.uid >= 0:
            os.setuid(self.uid)
        return os.path.join(self.base, username)
