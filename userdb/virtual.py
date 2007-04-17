#! /usr/bin/python

import __init__
import os

class new(__init__.UserDB):
    def init(self, config):
        self.uid = config.getint('Virtual', 'uid', None)
        self.gid = config.getint('Virtual', 'gid', None)
        self.base = config.get('Virtual', 'base', None)
        assert (self.uid and self.gid and self.base)

    def lookup(self, username):
        os.setgid(self.gid)
        os.setuid(self.uid)
        return os.path.join(self.base, username)
