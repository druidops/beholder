#!/usr/bin/python

import redis
import sys
import argparse
import bz2
import time
from termcolor import colored, cprint

redis_servers = ['redis.example.com']


def get_redis_available_files():
	""" Renvoi le dictionnaire des fichiers disponibles"""

	print "Warning, this is an expensive query !\n"

	# Contient tous les fichiers disponibles
	all_files = {}
	for redis_server in redis_servers:
		r = redis.Redis(host=redis_server, port=6379)

		# Recupere toutes les cles redis disponibles
		keys = r.keys('*')
		for item in keys:
			result = r.get(item)
			# Split de la cle redis qui est au format <hostname>#<file>
			hostname, key = item.split('#')
			if key in all_files:
				all_files[key] += 1
			else:
				all_files[key] = 1
	print "Available files (count)"
	if args.color:
		for k in sorted(all_files):
			print colored(all_files[k], 'blue'), colored(k, 'cyan')
	else:
		for k in sorted(all_files):
			print all_files[k], k

def cli_display(now,hostname,redis_ts,mtime_ts,line):
		redis_ts_str = time.strftime('%H:%M', time.localtime(int(redis_ts)))
		mtime_ts_str = time.strftime('%Y-%m-%dT%H:%M', time.localtime(int(mtime_ts)))
		if args.color:
			hostname=colored(hostname,'cyan')
			diff = now - float(redis_ts)
			if diff < 600:
				redis_ts_str=colored(redis_ts_str,'green')
			elif diff > 3600:
				redis_ts_str=colored(redis_ts_str,'red')
			else:
				redis_ts_str=colored(redis_ts_str,'yellow')

			mtime_ts_str=colored(mtime_ts_str,'blue')
			line=colored(line,'white','on_grey')

		print "%s (%s/%s) %s" % (hostname, redis_ts_str, mtime_ts_str, line)

def query_redis_servers():
	""" Retourne les valeurs disponibles pour la cle demandee"""

	# Pour comparaison fraicheur de la cle
	now = time.time()
	for redis_server in redis_servers:
		r = redis.Redis(host=redis_server, port=6379)

		# Recupere toutes les cles redis concernant le file demande
		keys = r.keys('*#%s' % file)
		for item in keys:
			result = r.get(item)
			# Split de la cle redis qui est au format <hostname>#<file>
			hostname, key = item.split('#')

			if result:
				# Split du format valeur stocke dans Redis 
				# <base64_encoded_data> <metadata1> <metadata2>...
				fields = result.split(' ')
				base64_data = fields[0]
				try:
					epoch_redis = fields[1]
					epoch_mtime = fields[2]
					file_md5    = fields[3]
				except IndexError:
					epoch_redis = 0
					epoch_mtime = 0
					file_md5    = "no_signature"

				try:
					c = bz2.decompress(base64_data.decode("base64"))
				except:
					c = "<error while decompressing bz2 data"
				if args.signature:
					cli_display(now,hostname,epoch_redis,epoch_mtime,file_md5)
				else:
					for line in c.split('\n'):
						cli_display(now,hostname,epoch_redis,epoch_mtime,line)
			else:
				print "No key found for %s" % key
				sys.exit(1)
		nb_keys = len(keys)
		print "### Keys found: %s ###" % nb_keys
		if nb_keys == 0 :
			print 'try the -ac switch for a list of all availablekeys'

########
# MAIN #
########
parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group()
group.add_argument("-f", "--file", help="File to query")
group.add_argument("-a", "--available", help="Show available files", action='store_true')
parser.add_argument("-c", "--color", help="Colorize output", action='store_true')
parser.add_argument("-s", "--signature", help="MD5 of file", action='store_true')

args = parser.parse_args()

file = args.file

if args.available:
	get_redis_available_files()
else:
	query_redis_servers()

