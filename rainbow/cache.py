#!/usr/bin/python2.7
# -*- coding: utf8 -*-

"""
Copyright [2014,2015] [beholder developers]

This file is part of beholder project

Provides a generic interface to allow rainbow to register resources.
 - get/set resources
 - dump to disk for persistence

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import cPickle, anydbm
from os.path import isfile

class rainbow_cache_error(Exception):
    pass

# the list of resources
_resources = {}

class rainbowCache():

  def __init__(self, resourceName, dbm_file='/var/cache/rainbow.index'):
    self.dbm_file = dbm_file

    if resourceName == "":
        raise rainbow_cache_error("Invalid resource name!")

    if resourceName in _resources.keys():
        pass

    else:
        _resources.setdefault(resourceName, {})
        if isfile(dbm_file):
            dbmIn = anydbm.open(dbm_file)
            if resourceName in dbmIn:
                _resources[resourceName] = cPickle.loads(dbmIn[resourceName])

  def update(self, resourceName, resourceContent):
    _resources[resourceName].update(resourceContent)

  def flush(self, resourceName):
    _resources[resourceName] = {}

  def dump(self):
    dbmOut = anydbm.open(self.dbm_file,'n')
    for resource in _resources:
      dbmOut[resource] = cPickle.dumps(_resources[resource], 1)
    dbmOut.close

  def __str__(self):
    out = ''
    for resource in _resources[resource]:
      out += "%s: %s\n" % (resource, _resources[resource])
    return out


