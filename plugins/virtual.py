#! /usr/bin/python

import __init__
import os
import re

path_re = re.compile(r'%((\d+)(\.\d+)?)?([udlm%])')

class PysievedPlugin(__init__.PysievedPlugin):
    def init(self, config):
        self.uid = config.getint('Virtual', 'uid', None)
        self.gid = config.getint('Virtual', 'gid', None)
        self.base = config.get('Virtual', 'base', None)
        self.hostdirs = config.getboolean('Virtual', 'hostdirs', False)
        self.homeformat = config.get('Virtual', 'homeformat', '%m')
        self.defaultdomain = config.get('Virtual', 'defaultdomain', '')
        assert (self.uid and self.gid)

    def lookup(self, params):
        # Determine format to use for virtual home directories
        if self.homeformat:
            home = self.homeformat
        elif self.hostdirs:
            home = os.path.join('%d', '%u')
        else:
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
        def repl(m):
            l = m.group(2)
            r = m.group(3)
            c = m.group(4)
            if c == '%':
                return '%'
            elif c == 'u':
                s = username
            elif c == 'd':
                s = domain
            elif c == 'l':
                s = login
            elif c == 'm':
                s = email
            if l:
                l = int(l)
                if r:
                    r = int(r[1:])
                    return s[l:l+r]
                else:
                    return s[:l]
            else:
                return s

        result = path_re.sub(repl, self.homeformat)

        if self.gid >= 0:
            os.setgid(self.gid)
        if self.uid >= 0:
            os.setuid(self.uid)

        return result

if __name__ == '__main__':
    c = __init__.TestConfig(uid=-1, gid=-1,
                            homeformat='/shared/spool/active/%d/%0.1u/%1.1u/%u/sieve/')
    n = PysievedPlugin(None, c)
    print n.lookup({'username': 'neale@woozle.org'})
