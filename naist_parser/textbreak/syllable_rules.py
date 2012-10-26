# -*- coding: utf8 -*-

import re

class SyllableRules:

	def __init__(self,rule_file=None):

		self.rules = []
		self.vars = {}

		if rule_file != None:
			self.load_rule(rule_file)

	def load_rule(self,rule_file):
		lines = open(rule_file).readlines()

		def map_vars(k):
			if k in self.vars: return self.vars[k]
			return k.strip("'")

		for line in lines:
			if line.strip() == '#variables' or line.strip() == '#rules':
				section = line.strip()	
				continue
			if section == '#variables' and line.strip() != '':
				k,v = line.strip().split(' := ')
				self.vars[k] = v.strip("'")
			elif section == '#rules' and line.strip() != '':
				tokens = line.strip().split('+')
				rule = reduce(lambda x,y:x+y,map(map_vars,tokens))
				self.rules.append(rule)

	def test(self,word):
		for rule in self.rules:
			if re.match('^'+rule+'$',word) != None:
				return True
		return False	

if __name__ == '__main__':
	sb = SyllableRules('dict/rules.txt')
	print sb.test('คุณห'.decode('utf8').encode('cp874'))
