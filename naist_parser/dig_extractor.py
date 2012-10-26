#!/usr/bin/python

import sys,os,re,os.path,math

from sqlobject import *

import xml.etree.ElementTree as ET
from common_utils import *

import cPickle
import copy
import md5
import pdb
import tempfile
from sqlobject import *

from dig_model import DigHead, DigRule, DigIndex, DigTree

sqlhub.processConnection = connectionForURI("mysql://khem:v,8;ps,k@vivaldi.cpe.ku.ac.th:3306/nonyipuk")

class DIGExtractor:
	def __init__(self):
		self.mtable = {}
		self.itable = {}
		self.xtable = {}
		self.ctable = {}

		self.roots = []
		self.Ps = {}
		self.Psa = {}
		self.Pi = {}

	def excepted_verb(self,word):
		return False

	def generate_rules(self,sstc_file):
		lines = open(sstc_file).readlines()
		for line in lines:
			if line.find('St:') == 0:
				sstc = line[3:].strip()
			if line.find('Ss:') == 0:
				text = line[3:].strip()
				parser = sstc_parser.SSTCParser()
				etree = parser.parse(sstc,text)
				root_pos = etree.getroot()[0].get('pos')
				if root_pos not in self.roots:
					self.roots.append(root_pos)
				self.analyze(etree)

	def dump_rules(self,rule_file='rules.p',index_file='index.p'):
		cPickle.dump(self.mtable,open(rule_file,'w'),protocol=-1)
		cPickle.dump(self.itable,open(index_file,'w'),protocol=-1)

		
	def print_readable_rules(self):
		print self.get_readable_rules()

	def get_readable_rules(self):
		text = ''
		text += '### Grammar Section ###\n'
		keys = self.mtable.keys()
		keys.sort()
		id = 1
		for key in keys:
			text += 'm:%s\n'%(key)
			for r in set(self.mtable[key]):
				text += '\t%s:%f\n'%(r,1.0*self.mtable[key].count(r)/len(self.mtable[key]))
		text += '\n\n### Index Section ###\n'
		keys = self.itable.keys()
		keys.sort()
		for key in keys:
			text += 'i:%s\n'%(key)
			for r in set(self.itable[key]):
				xkey = '%s+%s'%(key,r)
				text += '\t%s:%f:id=%d #%s\n'%(r,1.0*self.itable[key].count(r)/len(self.itable[key]),id,','.join(self.xtable[xkey]))
				id += 1
		text += '\n\n### Tree Section ###\n'
		keys = self.ctable.keys()
		keys.sort()
		for key in keys:
			text += 't:%s:'%(key)
			text += self.print_tree(self.ctable[key]) + '\n'
		return text

	def store_rules(self,rule,offset,key_word,etree,tu_id):
		prefix = key_word[:2]

		ikey = '%s%s'%(prefix,rule)
		if ikey not in self.itable:
			self.itable[ikey] = [offset]
		else:
			self.itable[ikey].append(offset)

		if key_word not in self.mtable:
			self.mtable[key_word] = [rule] 
		else:
			self.mtable[key_word].append(rule)

		xkey = '%s+%s'%(ikey,offset)
		if xkey not in self.xtable:
			self.xtable[xkey] = [str(tu_id)]
		elif str(tu_id) not in self.xtable[xkey]:
			self.xtable[xkey].append(str(tu_id))


	def _calculate_offset(self,tmp):
		L,R = [],[]
		table = {}
		for t in tmp:
			if t > 0:
				R.append(t)
			else:
				L.append(t)
		R.sort()
		i = 1
		for r in R:
			table[r] = i
			i += 1
		L.sort()
		L.reverse()
		i = -1
		for l in L:
			table[l] = i
			i -= 1
		return table

	def analyze(self,etree,tu_id=None):
		self.ctable[int(tu_id)] = etree.getroot()[0]
		#mode = 'simplified'
		mode = 'normal'
		rkey = {}
		# generate rules from a tree
		for node in etree.getiterator():
			pword = node.get('word')
			if pword == None or pword == '_': continue
			pid = int(node.get('snode').split('_')[0])
			ppos = node.get('pos').split('-')[0]
			sppos = get_simplified_pos(ppos)

			if node.get('snode') not in rkey:
				rkey[node.get('snode')] = ppos

			xcomps = []
			for child in node.getchildren():
				cword = child.get('word')
				if cword == '_': continue
				cid = int(child.get('snode').split('_')[0])
				cpos = child.get('pos').split('-')[0]
				scpos = get_simplified_pos(cpos)
				crole = child.get('role')

				if child.get('args') == 'adjunct':

					# extend complement arguments
					xsubtmp = []
					add_tmp,add_itmp = '',''
					for subchild in child.getchildren():
						if subchild.get('word') == '_': continue
						if subchild.get('args') == 'complement':
							ccpos = subchild.get('pos').split('-')[0]
							sccpos = get_simplified_pos(ccpos)
							scid = int(subchild.get('snode').split('_')[0])
							ccrole = subchild.get('role')

							if mode != 'simplified':
								xsubtmp.append((scid-cid,'[%s@%s]'%(ccpos,ccrole))) 
							else:
								xsubtmp.append((scid-cid,'[%s@%s]'%(sccpos,ccrole))) 
					if len(xsubtmp):
						xsubtmp.sort()
						add_tmp = ','.join([x[1] for x in xsubtmp])
						add_itmp = ','.join([str(x[0]) for x in xsubtmp])

					# specific adjunct rule
					tmp = ''
					if add_tmp == '':
						key_word = '%s:%s/%s'%('2',cword,cpos)
						if mode != 'simplified':
							tmp = '[%s] --> %s[%s@%s]'%(ppos,cword,cpos,crole)
						else:
							tmp = '[%s] --> %s[%s@%s]'%(sppos,cword,cpos,crole)

						if pid-cid > 0:
							itmp = '%d --> %d'%(1,0)
						else:
							itmp = '%d --> %d'%(-1,0)
					else:
						key_word = '%s:%s/%s'%('3',cword,cpos)
						if mode != 'simplified':
							tmp = '[%s] --> %s[%s@%s] --> %s'%(ppos,cword,cpos,crole,add_tmp)
						else:
							tmp = '[%s] --> %s[%s@%s] --> %s'%(sppos,cword,cpos,crole,add_tmp)

						itmp = '%d --> %d --> %s'%(pid-cid,0,add_itmp)
						# re-calculate offset
						t_offset = self._calculate_offset([pid-cid] + map(int,add_itmp.split(',')))
						x = map(str,map(lambda x:t_offset[x],map(int,add_itmp.split(','))))
						itmp = '%d --> %d --> %s'%(t_offset[pid-cid],0,','.join(x))

					self.store_rules(tmp,itmp,key_word,etree,tu_id)

					# generic adjunct rule
					if add_tmp == '':
						key_word = '%s:%s'%('2',cpos)
						if mode != 'simplified':
							tmp = '[%s] --> [%s@%s]'%(ppos,cpos,crole)
						else:
							tmp = '[%s] --> [%s@%s]'%(sppos,cpos,crole)
						rkey[child.get('snode')] = '2:%s'%tmp
					else:
						key_word = '%s:%s'%('3',cpos)
						if mode != 'simplified':
							tmp = '[%s] --> [%s@%s] --> %s'%(ppos,cpos,crole,add_tmp)
						else:
							tmp = '[%s] --> [%s@%s] --> %s'%(sppos,cpos,crole,add_tmp)
						rkey[child.get('snode')] = '3:%s'%tmp

					self.store_rules(tmp,itmp,key_word,etree,tu_id)

				elif child.get('args') == 'complement':
					if mode != 'simplified':
						xcomps.append((cid-pid,'[%s@%s]'%(cpos,crole)))
					else:
						xcomps.append((cid-pid,'[%s@%s]'%(scpos,crole)))

			if len(xcomps) and node.get('args') == 'complement':
				xcomps.sort()
				# specific complement rule
				tmp = '%s[%s] --> %s'%(pword,ppos,','.join([x[1] for x in xcomps]))
				x = [x[0] for x in xcomps]
				t_offset = self._calculate_offset(x)
				x = map(lambda x:t_offset[x],x)
				itmp = '%d --> %s'%(0,','.join(map(str,x)))
				
				key_word = '%s:%s/%s'%('1',pword,ppos)
				self.store_rules(tmp,itmp,key_word,etree,tu_id)

				# generic complement rule
				tmp = '[%s] --> %s'%(ppos,','.join([x[1] for x in xcomps]))
				key_word = '%s:%s'%('1',ppos)
				self.store_rules(tmp,itmp,key_word,etree,tu_id)
				if node.get('snode') not in rkey or rkey[node.get('snode')].split(':')[0] != 'a':
					rkey[node.get('snode')] = '1:%s'%tmp

		root = etree.getroot()
		self._update_prob_table(self.Pi,rkey[root[0].get('snode')],'YES')

		for node in etree.getiterator():
			snode = node.get('snode')
			if snode != None and snode in rkey:
				pid = int(node.get('snode').split('_')[0])
				ctmp,atmp = [],[]
				for child in node.getchildren():
					cid = int(child.get('snode').split('_')[0])
					if child.get('args') == 'complement' and child.get('word') != '_':
						ctmp.append((cid-pid,child.get('snode'),'c'))
					elif child.get('args') == 'adjunct' and child.get('word') != '_':
						atmp.append((cid-pid,child.get('snode'),'a'))
				ctmp.sort()
				atmp.sort()

				for i,t in enumerate(ctmp):
					if t[0] > 0:
						loc = 'R'
					else:
						loc = 'L'
					context = '%s+%s'%(rkey[snode],loc)
					A = rkey[t[1]]
					self._update_prob_table(self.Ps,str(A),context)

				if atmp == []:
					context = '%s+%d+%s'%(rkey[snode],0,True)
					self._update_prob_table(self.Psa,'STOP',context)
					continue

				for a in atmp:
					if a[0] > 0:
						loc = 'R'
					else:
						loc = 'L'
					context = '%s+%s'%(rkey[snode],loc)
					A = rkey[a[1]]
					self._update_prob_table(self.Psa,str(A),context)

	# P(A|B)
	def _update_prob_table(self,P,A,B):
		if B not in P:
			P[B] = {}
			P[B][A] = 1
		elif B in P and A not in P[B]:
			P[B][A] = 1
		elif B in P and A in P[B]:
			P[B][A] += 1
		return P

	def _print_tree(self,tree,s): # sstc format
		if tree.getchildren() == []:
			return '%s[%s]{%s}:%s/%s'%(encode_punc(tree.get('word')), \
                    tree.get('pos'),tree.get('role'),tree.get('snode'),tree.get('stree'))
		s = '%s[%s]{%s}:%s/%s'%(encode_punc(tree.get('word')), \
             tree.get('pos'),tree.get('role'),tree.get('snode'),tree.get('stree'))
		s += '('
		tmp = []
		for child in tree.getchildren():
			if child.get('id') != None:
				tmp.append((int(child.get('id')),child))
			else:
				tmp.append((-1,child))
		tmp.sort()
		for t in tmp:
			s += self._print_tree(t[1],s) + ','
		s = s.strip(',') + ')'
		return s

	def print_tree(self,tree):
		return self._print_tree(tree,'')

	def clear_db(self):
		DigHead.dropTable(ifExists=True)
		DigRule.dropTable(ifExists=True)
		DigIndex.dropTable(ifExists=True)
		DigTree.dropTable(ifExists=True)

		DigHead.createTable()
		DigRule.createTable()
		DigIndex.createTable()
		DigTree.createTable()

	def save_to_db(self):
		self.clear_db()
		tmp_table = {}
		# create DigTree and save them in the table
		for id,tree in self.ctable.items():
			obj = DigTree(tree_number=id,tree=self.print_tree(tree))
			tmp_table[int(id)] = obj

		for head in self.mtable:
			type = ''
			if head[0] == '1':
				type = 'I'
			elif head[0] == '2':
				type = 'II'
			elif head[0] == '3':
				type = 'III'
			etype = 'G'
			if head.rfind('/') > 0:
				etype = 'S'
			dighead_obj = DigHead(head=head[2:],type=type,etype=etype)
			for rule in set(self.mtable[head]):
				digrule_obj = DigRule(rule=rule,dighead=dighead_obj,n=self.mtable[head].count(rule))
				for idx in set(self.itable[head[0]+':'+rule]):
					digindex_obj = DigIndex(word_order=idx,digrule=digrule_obj,n=self.itable[head[0]+':'+rule].count(idx))
					for x in self.xtable[head[:2]+rule+'+'+idx]:
						digtree_obj = tmp_table[int(x)]
						digindex_obj.addDigTree(digtree_obj)
			

def main():
	extractor = DIGExtractor()
	lines = sys.__stdin__.readlines()
	tmp = []
	tu_id = 0
	for line in lines:
		if line.strip() == '':
			etree = mst2etree(tmp)
			extractor.analyze(etree,tu_id)
			tmp = []
			tu_id += 1
		else:
			tmp.append(line.strip())
	extractor.print_readable_rules()
	#extractor.save_to_db()
			
if __name__ == '__main__':
	main()
