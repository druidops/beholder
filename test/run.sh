#!/bin/bash
../rainbow/rainbow.py -ac
../rainbow/rainbow.py -f cf3/policy_server
../rainbow/rainbow.py -f cf3/policy_server -s
../rainbow/rainbow.py -f cf3/policy_server -c
#rm -f ./rainbow.cf
../rainbow/rainbow.py -ac -C ./rainbow.cf

pep8 ../rainbow/rainbow.py
