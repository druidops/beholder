#!/usr/bin/python2.7
# -*- coding: utf8 -*-

"""
Copyright [2014,2015] [beholder developers]

This file is part of beholder project

Provides a generic interface to allow rainbow to register resources.
 - get/put/update resources
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
import os

class rainbow_cache_error(Exception):
    pass

# the list of resources
_resources = {}

class rainbowCache():

  def __init__(self, resourceName=None, dbm_root='/tmp/rainbow/'):

    if resourceName == None:
        raise rainbow_cache_error("Invalid resource name!")

    if not os.path.exists(dbm_root):
        os.makedirs(dbm_root)

    self.resourceName = resourceName
    self.dbm_file = os.path.join(dbm_root, "%s.index" % resourceName)

    if resourceName in _resources.keys():
        pass

    else:
        _resources.setdefault(resourceName, {})
        if os.path.isfile(self.dbm_file):
            dbmIn = anydbm.open(self.dbm_file)
            for resource in dbmIn:
                _resources[resource] = cPickle.loads(dbmIn[resource])

  def update(self, resourceContent, resourceName=None):
    if resourceName == None:
      _resources.update(resourceContent)
    else:
      _resources[resourceName].update(resourceContent)

  def flush(self, resourceName=None):
    if resourceName == None:
      _resources = {}
    else:
      _resources[resourceName] = {}

  def dump(self):
    dbmOut = anydbm.open(self.dbm_file,'n')
    for resource in _resources:
      dbmOut[resource] = cPickle.dumps(_resources[resource], 1)
    dbmOut.close

  def getResources(self):
    return _resources[self.resourceName]

  def __str__(self):
    out = ''
    for resource in _resources:
      out += "%s: %s\n" % (resource, _resources[resource])
    return out

