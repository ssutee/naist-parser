import sys

import sys,os,re

import xml.etree.ElementTree as ET

from naist_parser.maxent_utils import generate_features,create_between_pos_table,extract_features
from naist_parser.common_utils import decode_punc,encode_number,get_simplified_pos

def extract_mira_features(s,t,units,b_table):
    pass

def main():
	lines = sys.__stdin__.readlines()
	tmp = []

	for line in lines:
		if line.strip() != '':
			tmp.append(line.strip())
		else:
			W = map(encode_number,map(str.strip,tmp[0].split('\t')))
			T = map(str.strip,tmp[1].split('\t'))
			H = map(str.strip,tmp[-1].split('\t'))

			if len(W) < 2:
				continue

			nW = []
			for i in range(len(W)):
				if T[i] == 'npn':
					nW.append('<npn>')
				else:
					nW.append(W[i])
			W = nW

			units = [(W[i].replace(' ','_'),T[i],H[i]) for i in range(len(W))]
			pairs = [(int(h),i+1) for i,h in enumerate(H)]

			b_table = create_between_pos_table(T)

			for i in range(1,len(W)+1,1):
				for j in range(1,len(W)+1,1):
					if i != j:
						if (i,j) in pairs:
							print 'Yes',extract_mira_features(i-1,j-1,units,b_table)
						else:
							print 'No',extract_mira_features(i-1,j-1,units,b_table)

			tmp = []
