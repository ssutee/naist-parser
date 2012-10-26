import re
import os.path
import xml.etree.ElementTree as ET
import htmllib
from cvxopt.base import spmatrix,matrix
from numpy import *

DIG_PARSER_PATH = os.path.join(os.path.expanduser('~'),'dig_parser')

Number = ['nnum']
Nlab = ['nlab']
Noun = ['ncn','nct','npn','ntit'] 
Relative = ['prel']
ModPronoun = ['ppos','prfx','prec']
Pronoun = ['pper','pdem','pind','pint'] 
Preverb = ['prev']
Postverb = ['vpost']
Verb = ['vi','vt','vcau','vcs','vex','honm'] 
Determiner = ['det','indet']
Adverb = ['adv']
Adverb_mark = ['advm1','advm2','advm3','advm4','advm5']
Conjunction = ['conj','conjc','conjncl']
Preposition = ['prep','prepc']
Prefix = ['pref1','pref2','pref3']
Particle = ['aff','part']
Negative = ['neg','negc']
Adjective = ['adj']
Classifier = ['cl']
Interjection = ['int']
Punctuation = ['punc']
Idiom = ['idm']
Passive_mark = ['psm']
Symbol = ['sym']
Space = ['blk']
Norm = ['norm']

GenericClass = Noun + Verb + Adverb + Prefix + Negative + Adjective + Classifier + Punctuation + Idiom \
				+ Passive_mark + Symbol + Space + Interjection
SpecificClass = Relative + Pronoun + Determiner + Adverb_mark + Conjunction + Preposition \
				+ Particle + Norm + Number + Nlab + Preverb + Postverb + ModPronoun 

all_pos = GenericClass + SpecificClass
all_pos.sort()

Complement = ['root','subj','csubj','dobj','iobj','pcomp',
                      'pobj','pred','cpred','sconj','conj','nom','advm']
Adjunct = ['modp','modr','appa','appr','rel','modt','modm',
                   'modl','moda','dprep','det','quan','cl','coord',
                   'neg','punc','svp','svs']

def compare_pos(t1,t2):
	if t1 == t2:
		return True
	if t1 in Prefix and t2 in ['ncn','npn']:
		return True
	if t2 in Prefix and t1 in ['ncn','npn']:
		return True
	return False

def load_pos(pos_file):
	ptable = {}
	for line in open(pos_file).readlines():
		tokens = line.split()
		word,pos = [],[]
		for token in tokens:
			if re.match('\w+',token):
				pos.append(token)
			else:
				word.append(token)
		if ' '.join(word) not in ptable:
			ptable[' '.join(word)] = set(pos)
		else:
			ptable[' '.join(word)] |= set(pos)
	return ptable

#pos_table = load_pos(os.path.join(DIG_PARSER_PATH,'pos_added.utf8.txt'))
#pos_table = load_pos(os.path.join(DIG_PARSER_PATH,'data/all.dict'))
#pos_table['_'] = ['blk']

def guess_pos(w,pos_table):
    ct = pos_table.get(w,['npn'])
    if len(w) == 1 and '~`!@#$%^&*()_-+={[]}\\|;:"\',<.>/?'.find(w) > -1:
        ct = ['punc']
    elif re.match('^[\d]+\.$',w) != None:
        ct = ['nlab']
    elif re.match('^[\d\.,]+$',w) != None:
        ct = ['nnum']
    return list(ct)

def get_simplified_pos(pos):
	if pos in Noun: return 'N'
	if pos in Pronoun: return 'N'
	if pos in Verb: return 'V'
	if pos in Determiner: return 'DET'
	if pos in Adverb: return 'ADV'
	if pos in Conjunction: return 'CONJ'
	if pos in Preposition: return 'PREP'
	if pos in Prefix: return 'PREFIX'
	if pos in Particle: return 'PART'
	if pos in Negative: return 'NEG'
	if pos in Adverb_mark: return 'ADVM'
	if pos in ModPronoun: return 'MP'
	return pos.upper()


all_simplified_pos = map(get_simplified_pos,all_pos)
all_simplified_pos = list(set(all_simplified_pos))
all_simplified_pos.sort()

def is_content_word(pos):
	if pos in Noun+Verb+Adjective+Adverb: return 'True'
	return 'False'

def decode_punc(input):
	if input == '-COMMA-': return ','
	if input == '-RRB-': return ')'
	if input == '-LRB-': return '('
	return input

def encode_punc(input):
	if input == ',': return '-COMMA-'
	if input == '(': return '-LRB-'
	if input == ')': return '-RRB-'
	return input

def is_known_word(word):
	return str(word in pos_table)

def is_number(word):
	word = word.replace(',','')
	try:
		float(word)
	except ValueError,e:
		return False
	return True

def encode_number(word):
	if is_number(word):
		return '<num>'
	return word

def get_type_of_roles(role):
	if role in Complement:
		return 'complement'
	elif role in Adjunct:
		return 'adjunct'
	return 'unknown'

def flink2etree(W,T,flink,elem,r=0,A=None):
	if r in flink:
		for c in flink[r]:
			sub_elem = ET.SubElement(elem,'node')
			sub_elem.set('word',W[c-1])
			sub_elem.set('pos',T[c-1])
			sub_elem.set('snode','%d_%d'%(c-1,c))
			if A != None:
				sub_elem.set('role',A[c-1])
				sub_elem.set('func',A[c-1])
				sub_elem.set('args',get_type_of_roles(A[c-1].split('/')[0]))
			flink2etree(W,T,flink,sub_elem,c,A)

def compute_stree(etree,x=999,y=0):
	i,j = map(int,etree.get('snode').split('_'))
	if i < x: x = i
	if j > y: y = j
	for node in etree.getchildren():
		x,y = compute_stree(node,x,y)
	return x,y

def add_stree(etree):
	stree = compute_stree(etree)
	etree.set('stree','%d_%d'%stree)
	for node in etree.getchildren():
		add_stree(node)


def mst2etree(lines):
	if len(lines) == 3 or len(lines) == 4:
		W = map(encode_number,map(str.strip,lines[0].split('\t')))
		T = map(str.strip,lines[1].split('\t'))
		A = None
		if len(lines) == 4:
			A = map(str.strip,lines[2].split('\t'))
			H = map(int,map(str.strip,lines[3].split('\t')))
		else:
			H = map(int,map(str.strip,lines[2].split('\t')))

		flink = {}
		for i in range(len(H)):
			h = H[i]
			if h not in flink:
				flink[h] = [i+1]
			else:
				flink[h] += [i+1]
		root = ET.Element('root')
		flink2etree(W,T,flink,root,r=0,A=A)
		add_stree(root[0])
		etree = ET.ElementTree(root)
		return etree
	return None

def load_digs_from_text(rule_file,mtable,itable):
	lines = open(rule_file).readlines()
	flag = None
	for line in lines:
		if line.strip() == '' or line[0] == '#': continue
		if line[:2] == 'm:':
			key = line[2:].strip()
			flag = 'm'
		elif line[:2] == 'i:':
			key = line[2:].strip()
			flag = 'i'
		elif line[0] == '\t':
			if flag == 'm':
				rule,prob = map(str.strip,line.split(':'))
				if key not in mtable:
					mtable[key] = [(rule,float(prob))]
				else:
					mtable[key].append((rule,float(prob)))
			elif flag == 'i':
				p = line.strip().find('#')
				rule,prob,id = line[:p].split(':')
				comment = line[p+1:].strip().strip('#')
				id = int(id[3:])
				if key not in itable:
					itable[key] = [(rule,float(prob),id,comment)]
				else:
					itable[key].append((rule,float(prob),id,comment))
	return mtable,itable


