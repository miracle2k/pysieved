#! /usr/bin/python

import __init__
import os
import re

class PysievedPlugin(__init__.PysievedPlugin):
    def init(self, config):
        self.uid = config.getint('Virtual', 'uid', None)
        self.gid = config.getint('Virtual', 'gid', None)
        self.base = config.get('Virtual', 'base', None)
        self.hostdirs = config.getboolean('Virtual', 'hostdirs', False)
        self.homeformat = config.get('Virtual', 'homeformat', '%m')
        self.defaultdomain = config.get('Virtual', 'defaultdomain', '')
        assert (self.uid and self.gid and self.base)

    def lookup(self, params):
        # Determine format to use for virtual home directories
        if self.homeformat:
            home = self.homeformat
        elif self.hostdirs:
            home = os.path.join('%d', '%u')
        else
            home = '%l'

        # Generate an absolute path from base if format is relative
        if not os.path.isabs(home):
            home = os.path.join(self.base, home)

        # Extract substitution elements
        login = params['username']
        parts = login.split('@', 1)
        username = parts[0]

        if len(parts) == 1:
            domain = self.default_domain
        else:
            domain = parts[1]

        if domain:
            email = '@'.join([ username, domain ])
        else:
            email = username

        # Perform pattern substitution
        result = ''
        next = 0
        p = re.compile('%[udlm]')
        iterator = p.finditer(home)
        for match in iterator:
            result += home[next:match.start()]
            if match.group() == '%u':
                result += username
            elif match.group() == '%d':
                result += domain
            elif match.group() == '%l':
                result += login
            elif match.group() == '%m':
                result += email
            next = match.end()
        result += home[next:]

        if self.gid >= 0:
            os.setgid(self.gid)
        if self.uid >= 0:
            os.setuid(self.uid)

        return result
