#!/usr/bin/python2.5

from naist_parser.maxent_utils import create_between_pos_table
from naist_parser.common_utils import mst2etree
from naist_parser.feature_utils import extract_label_features

import sys

def main():
    lines = sys.__stdin__.readlines()
    tmp = []
    for line in lines:
        if line.strip() == '':
            s_len = len(tmp[0])
            etree = mst2etree(tmp)
            root = etree.getroot()
            b_table = create_between_pos_table(tmp[1].strip().split())
            extract_label_features(root,s_len,b_table)
            tmp = []
        else:
            tmp.append(line)

if __name__ == '__main__':
    main()




