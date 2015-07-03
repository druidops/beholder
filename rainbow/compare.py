#!/usr/bin/python2.7
# -*- coding: utf8 -*-

"""
Copyright [2014,2015] [beholder developers]

This file is part of beholder project

Provides a generic interface to compare rainbow resources
 - input resources sets
 - output resources deltas computing

 # Here we split our custom Redis value format:
 # <base64_encoded_data> <epoch_redis> <epoch_mtime> <file_checksum>
 #         î___diff

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
import bz2

class rainbow_compare_error(Exception):
    pass

class rainbowCompare():

  def __init__(self, type):
    self.type = type

    pass

  def cmp(self, resourceA, resourceB):
    ''' resource[3] (md5sum) comparaison

    '''
    return resourceA.split(' ')[3] != resourceB.split(' ')[3]

  def diff(self, resourcesA, resourcesB, epoch_redis):
    # 1. select changed resources
    keysA = set(resourcesA.keys())
    keysB = set(resourcesB.keys())
    inter = keysA.intersection(keysB)
    addResources = keysB - inter
    remResources = keysA - inter
    chgResources = []
    for r in inter:
      if self.cmp(resourcesA[r],resourcesB[r]):
        chgResources.append(r)
    #print addResources, remResources
    #print chgResources
    # 2. foreach chgt diff compute
    for r in chgResources:
      rA = resourcesA[r].split(' ')
      rB = resourcesB[r].split(' ')
      dataA = bz2.decompress(rA[0].decode("base64"))
      dataB = bz2.decompress(rB[0].decode("base64"))
      A = set( dataA.split('\n') )
      B = set( dataB.split('\n') )
      interAB = A.intersection(B)
    # 3. print the diff
      for d in A - interAB:
        print "%s,%s,-,%s" % (epoch_redis, self.type, d)
      for d in B - interAB:
        print "%s,%s,+,%s" % (epoch_redis, self.type, d)
    for r in addResources:
      rB = resourcesB[r].split(' ')
      for d in bz2.decompress(rB[0].decode("base64")).split('\n'):
        print "%s,%s,+,%s" % (epoch_redis, self.type, d)
    pass

    # packages resource diff fmt
    # add "$(_ts),$(b),+,$(_cur)"
    # del "$(_ts),$(b),-,$(_prev)"
    # with _ts epoch_mtime, b packages, $(_cur)|$(_prev) line

if __name__ == '__main__':
  t1 = { 'h1': bz2.compress('<base64_encoded_data11>').encode("base64") + ' <epoch_redis> t1h1<epoch_mtime> <file_checksum11>',
         'h2': bz2.compress("t1h2<base64_encoded_data>\nt1h2<base64_encoded_data>").encode("base64") + ' <epoch_redis> t1h2<epoch_mtime> <file_checksum12>'
       }
  t2 = { 'h1': bz2.compress('<base64_encoded_data21>').encode("base64") + ' <epoch_redis> t2h1<epoch_mtime> <file_checksum21>',
         'h2': bz2.compress('t2h2<base64_encoded_data>').encode("base64") + ' <epoch_redis> t2h2<epoch_mtime> <file_checksum21>',
         'h3': bz2.compress("t2h31<base64_encoded_data>\nt2h32<base64_encoded_data>").encode("base64") + ' <epoch_redis> t2h3<epoch_mtime> <file_checksum>'
       }
  rc = rainbowCompare('packages')
  rc.diff(t1,t2)
