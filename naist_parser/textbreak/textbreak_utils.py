# -*- coding: utf8 -*-

import re
import string
import copy
import kjbuckets
from dijkstra import shortestPath
from priodict import priorityDictionary

# Adaption of kjGraph for weighted di-graph
class MyXGraph:
    def __init__(self):
        self.G = kjbuckets.kjGraph()
        self.W = {}

    def clear(self):
        self.G = kjbuckets.kjGraph()
        self.W = {}

    def add_edge(self,s,t,w=1):
        self.G[s] = t
        self.W['%s,%s'%(str(s),str(t))] = w

    def has_edge(self,s,t):
        return '%s,%s'%(str(s),str(t)) in self.W

    def delete_edge(self,s,t):
        try:
            self.G.delete_arc(s,t)
            del self.W['%s,%s'%(str(s),str(t))]
        except KeyError,e:
            pass

    def edges(self,s=None):
        if s != None:
            e = self.G.neighbors(s)
            if e == []: return []
            return map(lambda t:(s,t,self.W['%s,%s'%(str(s),str(t))]),e)
        else:
            i = self.G.items()
            if i == []: return []
            i.sort()
            return map(lambda x:(x[0],x[1],self.W['%s,%s'%(str(x[0]),str(x[1]))]),i)

    def nodes(self):
        x = self.G.keys() + self.G.values()
        x.sort()
        return list(set(x))

    def is_accessible(self,s,t):
        return t in self.G.reachable(s).items()

    def is_reachable(self,s,t):
        Q = [(-1,s,0)]
        while Q != []:
            x,start,y = Q[0]
            if start == t: return True
            del Q[0]
            next = self.edges(start)
            Q  = next + Q
        return False

    def to_dict(self):
        G = {}
        E = self.edges()
        E.reverse()
        for s,t,c in self.edges():
            if s not in G: 
                G[s] = {t:c}
            else: 
                G[s][t] = c
        return G

    def bigram_nodes(self,s):
        nodes = []
        for x,s_1,y in self.edges(s):
            for x,s_2,y in self.edges(s_1):
                nodes.append((s,s_1,s_2))
        return nodes

    def trigram_nodes(self,s):
        nodes = []
        for x,s_1,y in self.edges(s):
            for x,s_2,y in self.edges(s_1):
                for x,s_3,y in self.edges(s_2):
                    nodes.append((s,s_1,s_2,s_3))
        return nodes


class Utils:

    def get_char_type(c):
        code = ord(c)
        if code >= 224 and code <= 228:
            return '2'
        elif code == 210 or code == 211 or code == 208:
            return '3'
        elif code == 209 or (code >= 212 and code <= 218) or (code >= 231 and code <= 238):
            return '1'
        elif code >= 161 and code <= 206:
            return '4'
        return '5'
    get_char_type = staticmethod(get_char_type)

    def check_char_rules(text):
        if len(text) == 3:
            code = ''.join(map(Utils.get_char_type,text))
            if code in ['413','431','411','241']:
                return True
        elif len(text) == 2:
            code = ''.join(map(Utils.get_char_type,text))
            if code in ['41','43','24']:
                return True
        return False
    check_char_rules = staticmethod(check_char_rules)

    def is_symbol(c):
        if len(c) > 1:
            return 0
        if re.match('\w',c) != None:
            return 1
        if '~`!@#$%^&*()_-+={[]}\\|;:"\',<.>/?'.find(c) > -1:
            return 1
        return 0
    is_symbol = staticmethod(is_symbol)
    
    def is_number(number):
        if len(number) > 1:
            for d in number:
                if string.find('0123456789๑๒๓๔๕๖๗๘๙๐,.'.decode('utf8').encode('cp874'),d) == -1:
                    return 0
            return 1
        if string.find('0123456789๑๒๓๔๕๖๗๘๙๐'.decode('utf8').encode('cp874'),number) > -1:
            return 1
        return 0
    is_number = staticmethod(is_number)

    def is_thai_char(c):
        if len(c) > 1:
            return 0
        return not Utils.is_number(c) and not Utils.is_symbol(c)
    is_thai_char = staticmethod(is_thai_char)

    def is_thai_word(word):
        for c in word:
            if not Utils.is_thai_char(c) or re.match('\s',c) != None:
                return 0
        return 1
    is_thai_word = staticmethod(is_thai_word)   

    # Description: a method for the best path using Dijkstra's algorithm
    # G = dict representing a word graph
    # s = start 
    # t = target 
    # return set of edges and its score
    def find_the_best_path(G,s,t):
        path = shortestPath(G,s,t)
        flag = True
        score = 0
        edges = []
        for i in range(len(path))[1:]:
            s,t = path[i-1],path[i]
            if G[s][t] == 10e6: # cheking impossible result
                flag = False    
            score += G[s][t] 
            edges.append((s,t))
        return edges,score,flag
    find_the_best_path = staticmethod(find_the_best_path)


    def find_the_second_best_path(G,s,t):
        edges,score,flag = Utils.find_the_best_path(G,s,t)
        second_edges,second_score,second_flag = None,10e20,False
        for x,y in edges:
            tmp = G[x][y]
            G[x][y] = 10e6
            c_edges,c_score,c_flag = Utils.find_the_best_path(G,s,t)
            if c_score < second_score:
                second_edges,second_score,second_flag = c_edges,c_score,c_flag
            G[x][y] = tmp
        return second_edges,second_score,second_flag
    find_the_second_best_path = staticmethod(find_the_second_best_path)


    def _update_matrix(G,Ed):
        A = {}
        for x,y in [(x,y) for x in G for y in G[x]]:
            if x not in A:
                A[x] = {y:1}
            if (x,y) in Ed:
                A[x][y] = 10e6
            else:
                A[x][y] = G[x][y]
        return A
    _update_matrix = staticmethod(_update_matrix)


    def find_k_best_path(G,k,s,t):
        results = [None]
        edges,score,flag = Utils.find_the_best_path(G,s,t)
        if k == 1:
            return [(score,edges,flag)]
        results.append((score,edges,flag))
        T = set(edges)
        Q = []
        s_edges,s_score,s_flag = Utils.find_the_second_best_path(G,s,t)
        Q.append((s_score,s_edges,1,s_flag))
        for i in range(k+1)[2:]:
            Q.sort()
            cost_i,P_i,j,flag = Q.pop(0)
            results.append((cost_i,P_i,flag))
            T = T | set(P_i)
            Edj = T-set(results[j][1])
            Edi = T-set(P_i)
            B = Utils._update_matrix(G,Edj)
            edges,score,flag = Utils.find_the_second_best_path(B,s,t)
            Q.append((score,edges,j,flag))
            C = Utils._update_matrix(G,Edi)
            edges,score,flag = Utils.find_the_second_best_path(C,s,t)
            Q.append((score,edges,i,flag))
        return results[1:]
    find_k_best_path = staticmethod(find_k_best_path)


    def guess_pos(w,lex_prob=None):
        if lex_prob != None and w.decode('cp874').encode('utf8') in lex_prob:
            return lex_prob[w.decode('cp874').encode('utf8')].keys()

        ct = pos_table.get(w,['npn'])
        if len(w) == 1 and Utils.is_symbol(w):
            ct = ['punc']
        elif re.match('^[\d]+\.$','w') != None:
            ct = ['nlab']
        elif re.match('^[\d\.,]+$',w) != None:
            ct = ['nnum']

        return list(ct)
    guess_pos = staticmethod(guess_pos)
