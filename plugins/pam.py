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
import PAM

class new(__init__.new):
    def init(self, config):
        self.service = config.get('PAM', 'service', 'pysieved')

    def auth(self, params):
        def conv(auth, query_list, user_data):
            resp = []
            for query, qtype in query_list:
                if qtype == PAM.PAM_PROMPT_ECHO_OFF:
                    # Read string with echo turned off
                    resp.append((params['passwd'], 0))
                else:
                    return None
            return resp

        auth = PAM.pam()
        auth.start(self.service)
        auth.set_item(PAM.PAM_USER, params['username'])
        auth.set_item(PAM.PAM_CONV, conv)

        try:
            auth.authenticate()
            auth.acct_mgmt()
        except PAM.error:
            return None

        return True

if __name__ == '__main__':
    import sys

    class C:
        def get(*meh):
            return 'pysieved'

    n = new(C())
    print n.auth({'username': sys.argv[1],
                  'password': sys.argv[2]})
