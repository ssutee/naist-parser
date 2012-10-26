#!/usr/bin/python
# -*- coding: utf8 -*-

# author: Sutee Sudprasert 01/08/2007
# e-mail: sutee.s@gmail.com

# yakucut: Yet Another KU word segmenter
# version 0.01
# goal: the output is word graph

import sys,re,math,os,os.path,time
import trie

from syllable_rules import *
from textbreak_utils import *

class TextBreaker:
	def __init__(self):
		self.dict = {} # a set of dictionaries

	def load_dict(self,dict_name,dict_file):
		"""
		Load list of words into Trie

		@param dict_name: the dictionary name which will be refered later
		@type dict_name: string
		@param dict_file: the file that contains a list of words (TIS-620 or CP874)
		@type dict_file: string
		"""
		t = trie.Trie()
		for line in open(dict_file).readlines():
			t.add(line.split()[0].strip(),'')
		self.dict[dict_name] = t


	def pre_segment(self,text): 
		"""
		Compute marking points in given text following the unseperatable characters rules

		@param text: the input text
		@type text: string
		@return: a list of pairs of marking points
		"""
		n = len(text)
		i = 0
		results = []
		while i < n:
			if i+3 < n and Utils.check_char_rules(text[i:i+3]):
				results.append((i,i+3))
				i += 3
				continue
			elif i+2 < n and Utils.check_char_rules(text[i:i+2]):
				results.append((i,i+2))
				i += 2
				continue
			results.append((i,i+1))
			i += 1
		return results


	# Description: a general method for mapping dictionary into an string following the marked points
	# dict_name = dictionary
	# pairs = marked points [(s1,t1),(s2,t2),...] : ambiguities are allowed
	# text = the original string
	# return the word graph with all weigthed edages 1
	def map_dict(self,dict_name,pairs,text): #P'Bert's algorithm
		alist = []
		w_graph = MyXGraph()
		for s,t in pairs:
			del_tmp,add_tmp = [],[]
			for a in alist:
				if a[1] == s: 
					word = text[a[0]:t]
					if self.dict[dict_name].find(word) != None:
						w_graph.add_edge(a[0],t) 
					if not self.dict[dict_name].is_prefix(word):
						del_tmp.append((a[0],t))
					else:
						add_tmp.append((a[0],t))
			alist = list(set(alist) - set(del_tmp)) + add_tmp
			if self.dict[dict_name].find(text[s:t]) != None:
				w_graph.add_edge(s,t) 
			if len(alist) == 0 or self.dict[dict_name].is_prefix(text[s:t]): 
				alist.append((s,t))
		return w_graph

	
	# Description: delete paths which cannot reach the end of string
	# w_graph = the word graph
	# end = len(text)
	# return True if those paths were found
	def delete_hopeless_paths(self,w_graph,end):
		del_edges = []
		for s,t,c in w_graph.edges():
			if t != end and s > 0 and (s,t) not in del_edges:
				if not w_graph.is_accessible(t,end) or not w_graph.is_accessible(0,s):
					del_edges.append((s,t))
			elif t == end and s > 0 and (s,t) not in del_edges:
				if not w_graph.is_accessible(0,s):
					del_edges.append((s,t))
			elif t != end and s == 0 and (s,t) not in del_edges:
				if not w_graph.is_accessible(t,end):
					del_edges.append((s,t))
		for s,t in del_edges:
			if w_graph.has_edge(s,t):
				w_graph.delete_edge(s,t)

	# Description: try to find the end of a given word graph
	# w_graph = the word graph
	# return a list of ending edges
	def traverse_graph(self,w_graph):
		Q = [None]
		end = [(0,0)]
		while Q != []:
			if Q[0] ==  None:
				prev,start = -1,0
			else:
				prev,start,c = Q[0]
			if start > end[0][1]:
				end = [(prev,start)]
			elif start == end[0][1] and (prev,start) not in end and prev != -1:
				end.append((prev,start))
			next = w_graph.edges(start)
			del Q[0]
			Q = Q + next # breadth-first search
			Q = list(set(Q))
		return end

	def _split_thai_text(self,s,t,text):
		en,th = True,False
		marks = []
		if Utils.is_thai_char(text[s]):
			en,th = False,True
		for i in range(s,t,1):
			if Utils.is_thai_char(text[i]) and en:
				en,th = False,True
				marks.append(i)
			elif not Utils.is_thai_char(text[i]) and th:
				en,th = True,False
				marks.append(i)
		return [s] + marks + [t]

	# Description: a method for expanding all possible unknown words in a given word graph
	# w_graph = the word graph
	# end = len(text)
	# return a new word graph
	def expand_unknown_words(self,w_graph,text):
		end = len(text)
		ending = self.traverse_graph(w_graph)
		while ending[0][1] != end:
			for s,t in ending:
				count = 0
				for i in range(s+1,t,1): # back-tracking expanding
					if w_graph.edges(i) != []:
						count += 1
						m = self._split_thai_text(s,i,text)
						for j in range(len(m)):
							if j > 0: 
								w_graph.add_edge(m[j-1],m[j])
						if count == 1:
							break
				count = 0
				for i in range(t+1,end+1,1): # at-found expanding
					if w_graph.edges(i) != []:
						count += 1
						m = self._split_thai_text(t,i,text)
						for j in range(len(m)):
							if j > 0: 
								w_graph.add_edge(m[j-1],m[j])
						if count == 1:
							break
				m = self._split_thai_text(t,i,text)
				for j in range(len(m)):
					if j > 0: 
						w_graph.add_edge(m[j-1],m[j])
			ending = self.traverse_graph(w_graph)

		self.delete_hopeless_paths(w_graph,len(text))

		return w_graph

	# Description: a method for merging unknown syllables by heuristic rules
	# w_graph = the word graph
	# text = original string
	# syl_rules = SyllableRules class
	def merge_unknown_syllables(self,syl_rules,w_graph,text):
		found = True
		while found:
			found = False
			nodes = []
			for n in w_graph.nodes():
				nodes += w_graph.trigram_nodes(n)
			nodes.sort()
			for n in nodes:
				x,y,z = text[n[0]:n[1]],text[n[1]:n[2]],text[n[2]:n[3]]
				if len(y) == 1 and Utils.is_thai_char(y):
					if not w_graph.has_edge(n[0],n[2]) and syl_rules.test(x+y):
						w_graph.add_edge(n[0],n[2]) # x+y
						found = True
					elif not w_graph.has_edge(n[1],n[3]) and syl_rules.test(y+z):
						w_graph.add_edge(n[1],n[3]) # y+z
						found = True
					elif (x == 'ส'.decode('utf8').encode('cp874') or x == 'อ'.decode('utf8').encode('cp874')) and \
					     not w_graph.has_edge(n[1],n[3]) and Utils.is_thai_word(z):
						w_graph.add_edge(n[1],n[3]) # y+z
						found = True
					elif self.dict['lexicon'].find(x) != None and not w_graph.has_edge(n[1],n[3]) and Utils.is_thai_word(z):
						w_graph.add_edge(n[1],n[3]) # y+z
						found = True
					elif Utils.is_thai_word(x) and not w_graph.has_edge(n[0],n[2]):
						w_graph.add_edge(n[0],n[2]) # x+y
						found = True
					elif Utils.is_thai_word(z) and not w_graph.has_edge(n[1],n[3]):
						w_graph.add_edge(n[1],n[3]) # x+y
						found = True
				elif len(y) < 4  and not w_graph.has_edge(n[0],n[2]) \
				and Utils.is_thai_word(y) and self.dict['lexicon'].find(y) == None and 'ì' in y: #karan character
					w_graph.add_edge(n[0],n[2]) # x+y
					found = True
				elif syl_rules.test(x+y) and not w_graph.has_edge(n[0],n[2]):
					w_graph.add_edge(n[0],n[2]) # x+y
					found = True
				elif syl_rules.test(x+y+z) and not w_graph.has_edge(n[0],n[3]):
					w_graph.add_edge(n[0],n[3]) # x+y+z
					found = True

	# Description: a method for combining two adjacent unknown words together
	# w_graph = a word graph
	# text = original string
	# return True if two unknown words were combined
	def merge_unknown_words(self,w_graph,text):
		unk,tmp = {},[]
		for s,t,c in w_graph.edges():
			if self.dict['lexicon'].find(text[s:t]) == None:
				tmp.append((s,t))
				if s not in unk:
					unk[s] = [t]
				else:
					unk[s] += [t]
		tmp.reverse()
		while tmp != []:
			Q = [tmp.pop()]
			path = []
			while Q != []:
				s,t = Q.pop()
				path += [(s,t)]
				if t in unk:
					for x in unk[t]:
						Q.append((t,x))
						if (t,x) in tmp:
							tmp.remove((t,x))
			path.sort()
			if len(path) > 1:
				flag = True
				for x,y in path:
					if not Utils.is_thai_word(text[x:y]):
						flag = False
				if flag:
					w_graph.add_edge(path[0][0],path[-1][1])


	# Description: a method for computing edge weigth by using heuristic (maximum matching)
	# w_graph = the word graph
	# text = original text
	# return a new word graph with new edge weigth
	def compute_edge_weigth_by_heuristic(self,w_graph,text):
		new_graph = MyXGraph()
		min_score = 0
		for s,t,c in w_graph.edges():
			word = text[s:t]
			if self.dict['lexicon'].find(word) != None:
				score = 0.5
			elif len(word) == 1:
				score = 3
			else:
				score = 2.5
			new_graph.add_edge(s,t,score)
		return new_graph

	def compute_edge_weigth_for_training_corpus(self,w_graph,text):
		new_graph = MyXGraph()
		min_score = 0
		for s,t,c in w_graph.edges():
			word = text[s:t]
			if self.dict['lexicon'].find(word) != None:
				score = pow(3,t-s)
			else:
				score = pow(10,t-s)
			new_graph.add_edge(s,t,score)
		return new_graph

	def remove_useless_syllables(self,w_graph,dict_name,text):
		tmp_graph = MyXGraph()
		for s,t,c in w_graph.edges():
			tmp_graph.add_edge(s,t,c)

		del_edges = []
		for n in w_graph.nodes():
			tmp = w_graph.edges(n)
			if tmp == []:
				continue
			tmp = map(lambda x:(x[0],x[1]),tmp)
			t_max = max(tmp)
			if self.dict[dict_name].find(text[t_max[0]:t_max[1]]) == None:
				continue
			for s,t in tmp:
				for n_s,n_t,c in w_graph.edges(t):
					if n_t <= t_max[1] and \
					(self.dict[dict_name].find(text[s:t]) == None or \
					self.dict[dict_name].find(text[n_s:n_t]) == None):
						del_edges.append((s,t))
						del_edges.append((n_s,n_t))
		for s,t in del_edges:
			w_graph.delete_edge(s,t)
		self.delete_hopeless_paths(w_graph,len(text))

		if w_graph.edges() == []:
			for s,t,c in tmp_graph.edges():
				w_graph.add_edge(s,t,c)


	def cut_text(self,syl_rules,text,delimiter=' '):
		pairs = self.pre_segment(text)
		w_graph = self.map_dict('syllable-lexicon',pairs,text)
		w_graph = self.expand_unknown_words(w_graph,text)
		self.merge_unknown_syllables(syl_rules,w_graph,text)

		w_graph = self.compute_edge_weigth_by_heuristic(syl_rules,w_graph,text)
		E,s,f = Utils.find_the_best_path(w_graph.to_dict(),0,len(text))
		w_graph.clear()
		for s,t in E:
			w_graph.add_edge(s,t)
		pairs = map(lambda x:(x[0],x[1]),w_graph.edges())
		w_graph = self.map_dict('total',pairs,text)
		w_graph = self.expand_unknown_words(w_graph,text)
		self.remove_useless_syllables(w_graph,text)
		self.merge_unknown_words(w_graph,text)
		w_graph = self.compute_edge_weigth_by_heuristic(syl_rules,w_graph,text)

if __name__ == '__main__':
    tb = TextBreaker()
    lines = sys.__stdin__.readlines()
    for line in lines:
        line = line.strip()
        pairs = tb.pre_segment(line)
        tb.load_dict('test-dict','test.dict')
        w_graph = tb.map_dict('test-dict',pairs,line)
        w_graph = tb.expand_unknown_words(w_graph,line)
        tb.remove_useless_syllables(w_graph,'test-dict',line)
        for e in w_graph.edges():
            print e,line[e[0]:e[1]]
