#! /usr/bin/env python

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

import ConfigParser

class Config:
    def __init__(self, filename):
        try:
            self.c = ConfigParser.RawConfigParser()
            self.c.read(filename)
        except:
            self.c = None

    def get(self, section, option, default=None):
        try:
            return self.c.get(section, option)
        except:
            if default is None:
                raise KeyError("Must specify %s in section %s in config file" %
                               (option, section))
            else:
                return default

    def getint(self, section, option, default=None):
        try:
            return self.c.getint(section, option)
        except:
            if default is None:
                raise KeyError("Must specify %s in section %s in config file" %
                               (option, section))
            else:
                return default

    def getboolean(self, section, option, default=None):
        try:
            return self.c.getboolean(section, option)
        except:
            if default is None:
                raise KeyError("Must specify %s in section %s in config file" %
                               (option, section))
            else:
                return default
