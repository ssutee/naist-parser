#!/usr/bin/python

import xml.etree.ElementTree as ET

def _print_tree(tree,s):
	if tree.getchildren() == []:
		return '%s/%s@%s(%s)'%(tree.get('word'),tree.get('pos'),tree.get('role'),tree.get('snode'))
	s = '%s/%s@%s(%s)'%(tree.get('word'),tree.get('pos'),tree.get('role'),tree.get('snode'))
	s += '( '
	tmp = []
	for child in tree.getchildren():
		if child.get('id') != None:
			tmp.append((int(child.get('id')),child))
		else:
			tmp.append((-1,child))
	tmp.sort()
	for t in tmp:
		s += _print_tree(t[1],s) + ','
	s = s.strip(',') + ' )'
	return s

def print_tree(tree):
	return _print_tree(tree,'')


def flink2etree(W,T,flink,elem,r=0,A=None):
	if r in flink:
		for c in flink[r]:
			sub_elem = ET.SubElement(elem,'node')
			sub_elem.set('word',W[c-1])
			sub_elem.set('pos',T[c-1])
			sub_elem.set('snode','%d_%d'%(c-1,c))
			if A != None:
				sub_elem.set('role',A[c-1])
				sub_elem.set('args',get_type_of_roles(A[c-1]))
			flink2etree(W,T,flink,sub_elem,c,A)

def get_type_of_roles(role):
	complement = ['root','subj','csubj','dobj','iobj','pobj',
                     'nobj','pred','cpred','sconj','conj','nom']
	adjunct = ['modp','modr','appa','appr','rel','modt','modm',
                  'modl','moda','dprep','det','quan','cl','coord',
                  'neg','punc','svp','svs']
	if role in complement:
		return 'complement'
	if role in adjunct:
		return 'adjunct'
	return 'unknown'

def mst2etree(lines):
	if len(lines) == 3 or len(lines) == 4:
		W = lines[0].split()
		T = lines[1].split()
		H = map(int,lines[2].split())
		A = None
		if len(lines) == 4:
			A = lines[3].split()
		flink = {}
		for i in range(len(H)):
			h = H[i]
			if h not in flink:
				flink[h] = [i+1]
			else:
				flink[h] += [i+1]
		root = ET.Element('root')
		flink2etree(W,T,flink,root,r=0,A=A)
		etree = ET.ElementTree(root)
		return etree
	return None

