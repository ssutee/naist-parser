#!/usr/bin/env python

import urllib, urllib2
import json, codecs

json_input = codecs.open('test2.json', 'r', 'utf8').read()
values = {'data': json_input}

data = urllib.urlencode(values)
request = urllib2.Request('http://127.0.0.1:5000/parse', data)
response = urllib2.urlopen(request)

print json.loads(response.read())['result']
