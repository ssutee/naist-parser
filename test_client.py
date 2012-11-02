#!/usr/bin/env python

import urllib, urllib2
import json, codecs
import sys

json_input = codecs.open(sys.argv[1], 'r', 'utf8').read()
values = {'data': json_input}

data = urllib.urlencode(values)
request = urllib2.Request('http://127.0.0.1:5000/parse', data)
response = urllib2.urlopen(request)

ret = json.loads(response.read())

lines = ret['result'].split('\n')
print '\t'.join(map(lambda n: str(n+1), xrange(len(lines[0].split()))))
print ret['result']
