#!/usr/bin/python2.7
# -*- coding: utf8 -*-

"""
Copyright [2014] [beholder developers]

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
import time
import Queue
from termcolor import colored
from threading import Thread


REDIS_TIMEOUT = 2

redis_servers = ['redis1.internal',
                 'redis2.internal',
                 'redis3.internal',
                 'redis4.internal']

# Shared queue to store query results from Redis
output = Queue.Queue()


def formated_output(now, hostname, redis_ts, mtime_ts, line):
    """Colored output of a Redis entry plus metadata"""

    redis_ts_str = time.strftime('%H:%M',
                                 time.localtime(int(redis_ts)))
    mtime_ts_str = time.strftime('%Y-%m-%dT%H:%M',
                                 time.localtime(int(mtime_ts)))
    if args.color:
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

    print "%s (%s/%s) %s" % (hostname, redis_ts_str, mtime_ts_str, line)


def redis_query(redis_server, method, key):
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
                hostname, key = item.split('#')
                output.put((hostname, result))

    elif method == "KEYS":
        # Fetch all available keys
        items = r.keys('*')
        for item in items:
            # Split the key name, which format is <hostname>#<file>
            hostname, key = item.split('#')
            output.put(key)
    else:
        print "Not supported. You're doing it wrong."


def redis_get_all_keys():
    """ Fetch available keys from all Redis servers"""

    threads = []
    for redis_server in redis_servers:
        worker = Thread(target=redis_query, args=(redis_server, 'KEYS', '',))
        worker.start()
        threads.append(worker)

    for t in threads:
        t.join(REDIS_TIMEOUT)

    display_redis_all_keys()


def display_redis_all_keys():
    """ Print a nicely formatted summary of all keys found on
        all the Redis servers
    """

    uniq_files = {}

    while not output.empty():
        i = output.get()
        output.task_done()
        if i in uniq_files:
            uniq_files[i] += 1
        else:
            uniq_files[i] = 1

    if args.color:
        for k in sorted(uniq_files):
            print colored(uniq_files[k], 'blue'), colored(k, 'cyan')
    else:
        for k in sorted(uniq_files):
            print uniq_files[k], k


def display_redis_specific_key():
    """ Display contents of a specific key found over all the Redis servers"""

    # Actual timestamp of Redis query
    now = time.time()

    while not output.empty():
        (hostname, result) = output.get()
        output.task_done()

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

        try:
            c = bz2.decompress(base64_data.decode("base64"))
        except:
            c = "<error while decompressing bz2 data"
        if args.signature:
            formated_output(now, hostname, epoch_redis, epoch_mtime, file_md5)
        else:
            for line in c.split('\n'):
                formated_output(now, hostname, epoch_redis, epoch_mtime, line)


def redis_get_specific_key(key):
    """ Fetch contents of a specific key over all the Redis servers"""

    threads = []
    for redis_server in redis_servers:
        worker = Thread(target=redis_query, args=(redis_server, 'GET', key,))
        worker.start()
        threads.append(worker)

    for t in threads:
        t.join(REDIS_TIMEOUT)

    keys_found = output.qsize()
    display_redis_specific_key()

    print "### Keys found: %s ###" % keys_found
    if keys_found == 0:
        print 'try the -ac switch for a list of all available keys'


########
# MAIN #
########

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

args = parser.parse_args()

file = args.file

if args.available:
    redis_get_all_keys()
else:
    redis_get_specific_key(file)
