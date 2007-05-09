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
import MySQLdb

class new(__init__.new):
    def init(self, config):
        dbhost = config.get('MySQL', 'dbhost')
        dbuser = config.get('MySQL', 'dbuser')
        dbpass = config.get('MySQL', 'dbpass')
        dbname = config.get('MySQL', 'dbname')
        self.auth_query = config.get('MySQL', 'auth_query')
        self.user_query = config.get('MySQL', 'user_query')

        self.conn = MySQLdb.connect(host = dbhost,
                                    user = dbuser,
                                    passwd = dbpass,
                                    db = dbname)


    def __del__(self):
        self.conn.close()


    def auth(self, params):
        cursor = self.conn.cursor()
        cursor.execute(self.query % params)
        row = cursor.fetchone()
        cursor.close()

        # Only return true if there was a row result
        if row:
            return True
        return False


    def lookup(self, params):
        cursor = self.conn.cursor()
        cursor.execute(self.query % params)
        row = cursor.fetchone()
        assert row, 'No results from select (invalid user?)'
        cursor.close()

        return row[0]
