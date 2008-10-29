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

class PysievedPlugin:
    # Override this
    capabilities = 'fileinto reject'
    mechs = [ 'PLAIN' ]

    def __init__(self, log_func, config):
        self.log = log_func
        self.init(config)

    def init(self, config):
        # Override this
        pass

    def mechanisms(self):
        return self.mechs

    def do_sasl_first(self, mechanism, *args):
        """Handle the initial part of the SASL dialog

        This is just a wrapper around the auth() method
        if the requested mechanism is PLAIN.

        Returns a dictionary with the following elements :
        { 'result': 'OK' (pass), 'NO' (fail), 'BYE' (fatal) or 'CONT' (more),
          'msg': error string (fail or fatal) or server response (more),
          'username': authorized username (pass) }

        """

        if mechanism.upper() != 'PLAIN':
            return {'result': 'NO', 'msg': 'Unsupported authentication mechanism'}
        if len(args) != 1:
            return {'result': 'NO', 'msg': 'Must provide authentication credentials'}

        _, user, passwd = args[0].decode('base64').split('\0', 2)
        params = {'username': user, 'password': passwd}
        if self.auth(params):
            return {'result': 'OK', 'username': user}
        else:
            return {'result': 'NO', 'msg': 'Bad username or password'}


    def do_sasl_next(self, b64_string):
        """Handle the continuation of the SASL dialog

        Returns a dictionary with the following elements :
        { 'result': 'OK' (pass), 'NO' (fail), 'BYE' (fatal) or 'CONT' (more),
          'msg': error string (fail or fatal) or server response (more),
          'username': authorized username (pass) }

        """

        raise NotImplementedError()


    def auth(self, params):
        """Authenticate a user.

        Params will contain 'username' and 'password'.

        Returns true if authentication was successful.
        """

        raise NotImplementedError()


    def lookup(self, params):
        """Setuid and return home directory.

        Params will contain 'username' and 'password'.
        """

        raise NotImplementedError()


    def create_storage(self, params):
        """Return a storage object.

        Params will contain 'username', 'password', and 'homedir'
        """

        raise NotImplementedError()


class ScriptStorage:
    def __setitem__(self, k, v):
        if False:
            # If it doesn't validate, return ValueError
            raise ValueError('explanation')
        raise NotImplementedError()

    def __getitem__(self, k):
        raise NotImplementedError()

    def __delitem__(self, k):
        if self.is_active(k):
            raise ValueError('Script is active')
        raise NotImplementedError()

    def __iter__(self):
        raise NotImplementedError()

    def has_key(self, k):
        raise NotImplementedError()

    def is_active(self, k):
        raise NotImplementedError()

    def set_active(self, k):
        if k != None and not self.has_key(k):
            raise KeyError('Unknown script')
        raise NotImplementedError()

class TestConfig:
    def __init__(self, **kwargs):
        self.dict = kwargs.copy()

    def get(self, sect, key, default):
        return self.dict.get(key, default)

    def getboolean(self, sect, key, default):
        try:
            if self.dict[key]:
                return True
            else:
                return False
        except:
            return default

    def getint(self, sect, key, default):
        try:
            return int(self.dict[key])
        except:
            return default
