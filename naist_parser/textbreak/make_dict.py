#!/usr/bin/python

import sys

lines = sys.__stdin__.readlines()

tmp = []
for line in lines:
    tokens = line.strip().split()
    tmp += tokens

tmp = list(set(tmp))
tmp.sort()

for word in tmp:
    print word
