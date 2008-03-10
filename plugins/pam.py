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

class PysievedPlugin(__init__.PysievedPlugin):
    def init(self, config):
        self.service = config.get('PAM', 'service', 'pysieved')

    def auth(self, params):
        def conv(auth, query_list, *ign):
            if hasattr(auth, userdata):
                self.log(1, "PyPAM 0.5.0 may be buggy, we suggest using 0.4.2")
            resp = []
            for query, qtype in query_list:
                if qtype == PAM.PAM_PROMPT_ECHO_ON:
                    self.log(7, '< %s (%s)' % (query, 'PAM_PROMPT_ECHO_ON'))
                    resp.append(('', 0))
                    self.log(7, '> %s' % '')
                elif qtype == PAM.PAM_PROMPT_ECHO_OFF:
                    # Read string with echo turned off
                    self.log(7, '< %s (%s)' % (query, 'PAM_PROMPT_ECHO_OFF'))
                    resp.append((params['password'], 0))
                    self.log(7, '> %s' % params['password'])
                elif type == PAM.PAM_PROMPT_ERROR_MSG:
                    self.log(7, '< %s (%s)' % (query, 'PAM_PROMPT_ERROR_MSG'))
                    resp.append(('', 0))
                    self.log(7, '> %s' % '')
                elif type == PAM.PAM_PROMPT_TEXT_INFO:
                    self.log(7, '< %s (%s)' % (query, 'PAM_PROMPT_TEXT_INFO'))
                    resp.append(('', 0))
                    self.log(7, '> %s' % '')
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
