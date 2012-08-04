#!/usr/bin/env python

import json
import httplib2
import logging
import os
import sys

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

http = httplib2.Http()

def get(url):
    log.info('> GET %s' % (url,))
    response, data = http.request(url.encode('ascii'), 'GET')
    log.info('< %s' % (data,))
    return json.loads(data)

def post(url, data=None):
    log.info('POST %s [%s]' % (url, data))
    response, data = http.request(url.encode('ascii'), 'POST', json.dumps(data or '{}'), 
        {'Content-Type': 'application/json; charset=utf-8'} )
    log.info('< %s' % (data,))
    return json.loads(data)

def put(url, data=None):
    log.info('PUT %s [%s]' % (url, data))
    response, data = http.request(url.encode('ascii'), 'PUT', json.dumps(data or '{}'), 
        {'Content-Type': 'application/json; charset=utf-8'} )
    log.info('< %s' % (data,))
    return json.loads(data)

def put_raw(url, data=None):
    log.info('PUT %s <raw>' % (url,))
    response, data = http.request(url.encode('ascii'), 'PUT', data or '')
    log.info('< %s' % (data,))
    return json.loads(data)

username = 'user1'

user = get('http://localhost:8888/' + username)

bucket_url = post(user['resources']['buckets']['url'])['url']
bucket = get(bucket_url)
bucket_files = bucket['resources']['files']['url']

for path in sys.argv[1:]:
    filename = os.path.basename(path)
    log.info('Uploading %s' % (filename,))
    put_raw(bucket_files + '/' + filename, open(path).read())

bucket = get(bucket_url)
assert len(bucket['sources']) > 0
src = bucket['sources'].keys()[0]

layer_url = post(user['resources']['layers']['url'], {'bucket': bucket['urn']})['url']

put(layer_url, {'name': 'added from command line', 'source': {'bucket': bucket['urn'], 'source': src}})

layer = get(layer_url)

map_url = get(user['resources']['maps']['url'])['resources'][0]['url']
map_ = get(map_url)
put(map_['resources']['layers']['url'], {'urn': layer['urn']})

