#!/usr/bin/python2.5

import sys
from naist_parser.mira import *

def train():
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    mira = MIRA()
    mira.read_training_file(input_file)
    mira.train(N=10,k=5)
    mira.save_model(output_file)

if __name__ == '__main__':
    train()
