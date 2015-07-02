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


class rainbow_compare_error(Exception):
    pass

class rainbowCompare():

  def __init__(self, type):
    self.type = type

    pass

  def cmp(self, resourceA, resourceB):
    return resourceA.split(' ')[3] != resourceB.split(' ')[3]

  def diff(self, resourcesA, resourcesB):
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
      A = set( resourcesA[r].split(' ')[0].split('\n') )
      B = set( resourcesB[r].split(' ')[0].split('\n') )
      interAB = A.intersection(B)
    # 3. print the diff
      for d in A - interAB:
        print "%s,%s,-,%s" % (resourcesA[r].split(' ')[2], self.type, d)
      for d in B - interAB:
        print "%s,%s,+,%s" % (resourcesB[r].split(' ')[2], self.type, d)
    for r in addResources:
      for d in resourcesB[r].split(' ')[0].split('\n'):
        print "%s,%s,+,%s" % (resourcesB[r].split(' ')[2], self.type, d)
    pass

    # packages resource diff fmt
    # add "$(_ts),$(b),+,$(_cur)"
    # del "$(_ts),$(b),-,$(_prev)"
    # with _ts epoch_mtime, b packages, $(_cur)|$(_prev) line

if __name__ == '__main__':
  t1 = { 'h1': '<base64_encoded_data11> <epoch_redis> t1h1<epoch_mtime> <file_checksum11>',
         'h2': "t1h2<base64_encoded_data>\nt1h2<base64_encoded_data> <epoch_redis> t1h2<epoch_mtime> <file_checksum12>"
       }
  t2 = { 'h1': '<base64_encoded_data21> <epoch_redis> t2h1<epoch_mtime> <file_checksum21>',
         'h2': 't2h2<base64_encoded_data> <epoch_redis> t2h2<epoch_mtime> <file_checksum21>',
         'h3': "t2h31<base64_encoded_data>\nt2h32<base64_encoded_data> <epoch_redis> t2h3<epoch_mtime> <file_checksum>"
       }
  rc = rainbowCompare('packages')
  rc.diff(t1,t2)
