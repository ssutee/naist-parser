#!/usr/bin/python2.5

from prioqueue import PriorityQueue
import copy

class KBest:
    def __init__(self,k,x,y):
        """
        x and y is a list of tuples or lists -> (score,obj1,obj2)
        """
        self.x = x
        self.y = y

        self.C = PriorityQueue()
        self.p = []
        self.k = k
        self.tmp = []

    def _insert_queue(self,i,j):
        self.C.put((self.x[i][0]+self.y[j][0],[i,j]))
        self.tmp.append([i,j])

    def mult(self,k=None):
        if k != None:
            self.k = k

        self._insert_queue(0,0)
        while len(self.p) < self.k and not self.C.empty():
            self._append_next()

        return self.p

    def _append_next(self):
        s,v = self.C.get()
        self.tmp.remove(v)

        self.p.append((s,v))
        for i in range(2):
            vc = copy.deepcopy(v)
            vc[i] += 1
            if vc[0] < len(self.x) and vc[1] < len(self.y) and vc not in self.tmp:
                self._insert_queue(vc[0],vc[1])

def test():
    x = [(0,'a'),
         (4,'b'),
         (2,'c'),
         (4,'d'),
         (1,'e')]
    x.sort()
    y = [(1,'f'),
         (4,'g'),
         (8,'h'),
         (2,'i'),
         (0,'j')]
    y.sort()
    k_best = KBest(6,x,y)

    print 'x =',x
    print 'y =',y
    for s,(i,j) in k_best.mult():
        print s,x[i],y[j]

if __name__ == '__main__':
    test()
