import sys,cPickle


class ProbabilityModel:
	def __init__(self,filename):
		# filename = pickle file
		input = open(filename)
		self.p_table = cPickle.load(input)
		input.close()

	def _count_freq(self,t1,t2,distance,direction=None):
		if direction == None:
			return self._count_freq(t1,t2,distance,0) + self._count_freq(t1,t2,distance,1)
		key = '%s %s %d'%(t1,t2,direction)
		if key not in self.p_table:
			return 0
		if key in self.p_table and distance not in self.p_table[key]:
			return 0
		return self.p_table[key][distance] 

	def get_prob(self,t1,t2,distance,direction):
		n1 = float(self._count_freq(t1,t2,1,direction))
		n2 = float(self._count_freq(t1,t2,2,direction))
		n3 = float(self._count_freq(t1,t2,3,direction))

		m1 = self._count_freq(t1,t2,1) 
		m2 = self._count_freq(t1,t2,2) 
		m3 = self._count_freq(t1,t2,3) 

		a1,a2,a3,a4,e = 0.5, 0.3, 0.1, 0.1, 0.0001
		
		if distance == 1:
			if m1 != 0: x1 = a1*(n1/m1) 
			else: x1 = 0
			if m1+m2 != 0: x2 = a2*(n2/(m1+m2)) 
			else: x2 = 0
			if m1+m3 != 0: x3 = a3*(n3/(m1+m3)) 
			else: x3 = 0
			return x1+x2+x3+(a4*e)
		if distance == 2:
			if m2 != 0: x1 = a1*(n2/m2) 
			else: x1 = 0
			if m2+m1 != 0: x2 = a2*(n1/(m2+m1)) 
			else: x2 = 0
			if m2+m3 != 0: x3 = a3*(n3/(m2+m3)) 
			else: x3 = 0
			return x1+x2+x3+(a4*e)
		if distance == 3:
			if m3 != 0: x1 = a1*(n3/m3) 
			else: x1 = 0
			if m3+m1 != 0: x2 = a2*(n1/(m3+m1)) 
			else: x2 = 0
			if m3+m2 != 0: x3 = a3*(n2/(m3+m2)) 
			else: x3 = 0
			return x1+x2+x3+(a4*e)
