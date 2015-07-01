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

  def __init__(self):

    pass


  def diff(self, cur_resource, new_resource):
    # 1. select changed resources
    # 2. foreach entry calculate the diff (resource depend)
    # 3. print the diff
    pass

    # packages resource diff fmt
    # add "$(_ts),$(b),+,$(_cur)"
    # del "$(_ts),$(b),-,$(_prev)"
    # with _ts epoch_mtime, b packages, $(_cur)|$(_prev) line

