#!/usr/bin/python2.7
# -*- coding: utf8 -*-

"""
Copyright [2014,2015] [beholder developers]

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

import redis
import argparse
import bz2
import Queue
import sys
import os
import time
import ConfigParser
from threading import Thread

from termcolor import colored
from cache import rainbowCache
from compare import rainbowCompare

REDIS_TIMEOUT = 120


class Rainbow:

    def __init__(self, cmdln_args, redis_servers, redis_timeout):
        self.args = cmdln_args
        self.cached = False
        self.redis_timeout = redis_timeout
        self.redis_servers = redis_servers
        # Shared queue to store query results from Redis
        self.output_queue = Queue.Queue()

    def run(self):

        if self.args.available:
            self.redis_get_all_keys()
        else:
            self.redis_get_specific_key(self.args.file)

    def formated_output(self, now, hostname, redis_ts, mtime_ts, line):
        """Colored output of a Redis entry plus metadata"""

        redis_ts_str = time.strftime('%H:%M',
                                     time.localtime(int(redis_ts)))
        mtime_ts_str = time.strftime('%Y-%m-%dT%H:%M',
                                     time.localtime(int(mtime_ts)))
        if self.args.color:
            hostname = colored(hostname, 'cyan')
            diff = now - float(redis_ts)
            if diff < 600:
                redis_ts_str = colored(redis_ts_str, 'green')
            elif diff > 3600:
                redis_ts_str = colored(redis_ts_str, 'red')
            else:
                redis_ts_str = colored(redis_ts_str, 'yellow')

            mtime_ts_str = colored(mtime_ts_str, 'blue')
            line = colored(line, 'white', 'on_grey')

        if self.args.verbose:
            print "%s (%s/%s) %s" % (hostname, redis_ts_str, mtime_ts_str, line)

    def redis_query(self, redis_server, method, key):
        """ Query a Redis server (within a thread)
            and write results to the shared queue"""

        print "Querying_redis_server %s" % redis_server

        r = redis.Redis(host=redis_server, port=6379)

        if method == "GET":
            # Fetch all keys matching the requested pattern
            items = r.keys('*#%s' % key)
            for item in items:
                result = r.get(item)
                if result:
                    # Split the key name, which format is <hostname>#<file>
                    try:
                        hostname, key = item.split('#')
                    except ValueError:
                        print "Warning - Skipping key with invalid \
                                format: %s" % item
                        continue
                    self.output_queue.put((hostname, result))

        elif method == "KEYS":
            # Fetch all available keys
            items = r.keys('*')
            for item in items:
                # Split the key name, which format is <hostname>#<file>
                try:
                    hostname, key = item.split('#')
                except ValueError:
                    print "Warning - Skipping key with invalid \
                            format: %s" % item
                    continue
                self.output_queue.put(key)
        else:
            print "Not supported. You're doing it wrong."

    def redis_get_all_keys(self):
        """ Fetch available keys from all Redis servers"""

        threads = []
        for redis_server in self.redis_servers:
            worker = Thread(target=self.redis_query,
                            args=(redis_server, 'KEYS', '',))
            worker.start()
            threads.append(worker)

        for t in threads:
            t.join(REDIS_TIMEOUT)

        self.display_redis_all_keys()

    def display_redis_all_keys(self):
        """ Print a nicely formatted summary of all keys found on
            all the Redis servers
        """

        uniq_files = {}

        while not self.output_queue.empty():
            i = self.output_queue.get()
            self.output_queue.task_done()
            if i in uniq_files:
                uniq_files[i] += 1
            else:
                uniq_files[i] = 1

        if self.args.color:
            for k in sorted(uniq_files):
                # 13 here because of color escape characters \033[xx(x)
                print "%13s %s" % (colored(uniq_files[k], 'blue'),
                                   colored(k, 'cyan'))
        else:
            for k in sorted(uniq_files):
                print "%5s %s" % (uniq_files[k], k)

    def display_redis_specific_key(self, key):
        """ Display contents of a specific key through all the Redis servers"""

        # Actual timestamp of Redis query
        now = time.time()

        if self.args.logstash:
            self.cached = True
            cache = rainbowCache(key)
            redis_resources = {}

        while not self.output_queue.empty():
            (hostname, result) = self.output_queue.get()
            self.output_queue.task_done()

            # Here we split our custom Redis value format:
            # <base64_encoded_data> <epoch_redis> <epoch_mtime> <file_checksum>

            fields = result.split(' ')
            base64_data = fields[0]
            try:
                epoch_redis = fields[1]
                epoch_mtime = fields[2]
                file_md5 = fields[3]
            except IndexError:
                epoch_redis = 0
                epoch_mtime = 0
                file_md5 = "no_signature"

            if self.cached:
                redis_resources[hostname] = "%s %s %s %s" % (base64_data, epoch_redis, epoch_mtime, file_md5)
                continue

            try:
                c = bz2.decompress(base64_data.decode("base64"))
            except:
                c = "<error while decompressing bz2 data"

            if self.args.signature:
                self.formated_output(now, hostname, epoch_redis,
                                     epoch_mtime, file_md5)
            else:
                for line in c.split('\n'):
                    self.formated_output(now, hostname, epoch_redis,
                                         epoch_mtime, line)
        if self.args.logstash:
            c = rainbowCompare(key)
            c.diff(cache.getResources(), redis_resources)
            cache.update(redis_resources, key)
            cache.dump()

    def redis_get_specific_key(self, key):
        """ Fetch contents of a specific key over all the Redis servers"""

        threads = []
        for redis_server in self.redis_servers:
            worker = Thread(target=self.redis_query,
                            args=(redis_server, 'GET', key,))
            worker.start()
            threads.append(worker)

        for t in threads:
            t.join(REDIS_TIMEOUT)

        keys_found = self.output_queue.qsize()
        self.display_redis_specific_key(key)

        if self.args.verbose:
            print "### Keys found: %s ###" % keys_found
        if keys_found == 0:
            print 'try the -ac switch for a list of all available keys'


def autogen_conf(f):
    config.add_section('query_servers')
    config.set('query_servers', 'hostnames', 'redis1.example.org, \
               redis2.example.org')
    config.write(open(f, 'w'))
    print("Created an empty config file at %s." % f)
    print("Please modify it & re-run this command.")
    sys.exit(1)


def test_default_conf(f):
    if redis_servers[0] == 'redis1.example.org':
        print("Please set your own redis instance in %s file \
              and re-run this command." % f)
        sys.exit(1)

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-f", "--file",
                       help="File to query")
    group.add_argument("-a", "--available",
                       help="Show available files", action='store_true')
    parser.add_argument("-c", "--color",
                        help="Colorize output", action='store_true')
    parser.add_argument("-s", "--signature",
                        help="MD5 of file", action='store_true')
    parser.add_argument("-l", "--logstash",
                        help="compute logstash output", action='store_true')
    parser.add_argument("-v", "--verbose",
                        help="verbose stdout informations", action='store_true')
    parser.add_argument("-C", "--conffile",
                        help="Configuration file to Use")

    args = parser.parse_args()

    config = ConfigParser.RawConfigParser()
    if args.conffile:
        conffile = args.conffile
    else:
        conffile = os.path.abspath(os.path.expanduser('~/.rainbow.cf'))
    if not os.path.exists(conffile):
        autogen_conf(conffile)

    config.read(conffile)
    redis_servers = config.get('query_servers', 'hostnames').split(',')
    test_default_conf(conffile)
    rb = Rainbow(args, redis_servers, REDIS_TIMEOUT)
    rb.run()
