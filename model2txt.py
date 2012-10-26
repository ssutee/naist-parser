#!/usr/bin/python2.5

from maxent import MaxentModel

import sys

model_file = sys.argv[1]

m = MaxentModel()
m.load(model_file)
m.save(model_file+'.txt')

