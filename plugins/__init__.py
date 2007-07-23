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

class new:
    # Override this
    capabilities = 'fileinto reject'

    def __init__(self, log_func, config):
        self.log = log_func
        self.init(config)

    def init(self, config):
        # Override this
        pass


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


