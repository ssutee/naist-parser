#-*- coding:utf8 -*-

import sys,pdb,math,os,os.path,md5,time

from maxent import MaxentModel
import t3

from common_utils import *
from maxent_utils import *
from probability_model import *
from TrieETrees import *

from feature_utils import compute_label
from mira import MIRA, TrainingFeatures
from k_best import KBest

from textbreak.simple_textbreak import TextBreaker
from textbreak.textbreak_utils import MyXGraph

from distutils.sysconfig import get_python_lib

class UnknownArgumentError(Exception):
    def __init__(self, value, opt):
        self.value = value
        self.opt = opt
    def __str__(self):
        return repr(self.value) + ' : ' + str(self.opt)

class ParameterError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return str(value) + ' is impossible parameter.'

class NAISTParser:
    def __init__(self,
                    model_file=None,
                    label_model_file=None,
                    dig_file=None,
                    excluded_file=None,
                    dict_file=None,
                    pos_file=None,
                    type='pos',
                    model_type='maxent',
                    pos_style='naist',
                    k_best=1,
                    bad_allow=0,
                    bias=1,
                    multi_results=False,
                    lang_model=False
                    ):
        """
        @param prefix:The name (without extension) of ngram and lexicon file
            for t3 tagger model
        @type prefix: string
        @param model_file: Maxent parsing model file
        @type model_file: string
        @excluded_file: A file that contains tree id that will not be used for
            extracting DIGs
        @type excluded_file: string
        @param dict_file: A list of words used for word segmenting
        @type dict_file: string
        @param label_model_file: Maxent grammatical function labeling model file
        @type label_model_file: string

        dict_file are needed for parsing raw input
        """
        self.k_best = k_best
        self.bad_allow = bad_allow
        self.bias = bias

        self.model_type = model_type
        self.pos_style = pos_style
        
        self.multi_results = multi_results
        self.use_lang_model = lang_model
        
        self.dict_file = dict_file
        self.pos_file = pos_file
        if pos_file != None:
            self.pos_table = load_pos(pos_file)
        self.dig_file = dig_file
        self.label_model_file = label_model_file
        self.roots = ['vt','vi','vcau','vex','vcs','conj']

        if model_file != None and model_type == 'maxent':
            self.maxent_model = MaxentModel()
            sys.__stderr__.write('loading model...\n')
            self.maxent_model.load(model_file)
            sys.__stderr__.write('done\n')

        if model_file != None and model_type == 'mira':
            self.mira_model = MIRA()
            self.mira_model.load_model(model_file)

        if label_model_file != None:
            self.label_maxent_model = MaxentModel()
            self.label_maxent_model.load(label_model_file)

        if excluded_file != None:
            self.excluded = []
            self.excluded = map(int,open(excluded_file).read().strip().split())

        if type == 'cut' or type == 'raw':
            ngram_file1 = os.path.join('data','thai-t3.ngram')
            ngram_file2 = os.path.join(get_python_lib(0,0,'/usr/local'),'naist_parser','data','thai-t3.ngram')
            if os.path.exists(ngram_file1):
                t3.set_model_file(ngram_file1)
            elif os.path.exists(ngram_file2):
                t3.set_model_file(ngram_file2)
            
            lex_file1 = os.path.join('data','thai-t3.lex')
            lex_file2 = os.path.join(get_python_lib(0,0,'/usr/local'),'naist_parser','data','thai-t3.lex')
            if os.path.exists(lex_file1):
                t3.set_dict_file(lex_file1)
            elif os.path.exists(lex_file2):
                t3.set_dict_file(lex_file2)

            self.trigram_model = t3.new_model()
            t3.my_init_model(self.trigram_model)

        if dict_file != None:
            self.tb = TextBreaker()
            self.tb.load_dict(dict_file,dict_file)
            self.dict_file = dict_file
        elif dict_file == None and type == 'raw':
            raise ParameterError(dict_file)

        if dig_file != None:
            self.mtable,self.itable = self._load_rules_from_text(dig_file)

    def _load_rules_from_text(self, rule_file):
        lines = open(rule_file).readlines()
        flag = None
        mtable,itable = {},{}
        for line in lines:
            if line.strip() == '' or line[0] == '#': continue
            if line[:2] == 'm:':
                key = line[2:].strip()
                flag = 'm'
            elif line[:2] == 'i:':
                key = line[2:].strip()
                flag = 'i'
            elif line[0] == '\t':
                tokens = line.strip().split(':')
                if len(tokens) == 2:
                    rule,prob = map(str.strip,line.split(':'))
                elif len(tokens) == 3:
                    rule,prob,rest = map(str.strip,line.split(':'))
                    p = rest.find('#')
                    id = int(rest[:p].strip().split('=')[1])
                    ref_tid = rest[p+1:].strip().split(',')
                if flag == 'm':
                    if key not in mtable:
                        mtable[key] = [(rule,float(prob))]
                    else:
                        mtable[key].append((rule,float(prob)))
                elif flag == 'i':
                    if key not in itable:
                        itable[key] = [(rule,float(prob),id,ref_tid)]
                    else:
                        itable[key].append((rule,float(prob),id,ref_tid))
        return mtable,itable

    def _create_acc(self,nodes,graph):
        """
        @param nodes: a set of nodes (a tuple containing starting point, ending point, word, and pos)
        @type nodes: list
        @param graph: a morphogical graph
        @type graph: MyXGraph
        @return: a dict for checking any two nodes in a graph whether is reachable or not
        """
        acc = {0:{1:1}}
        for i,node_i in enumerate(nodes):
            acc[0][i+1] = 1
            for j,node_j in enumerate(nodes):
                if i != j and i < j and (node_i[1] <= node_j[0]) and\
                 graph.is_reachable(node_i[1],node_j[0]):
                    if i+1 not in acc:
                        acc[i+1] = {j+1:1}
                    else:
                        acc[i+1][j+1] = 1
        return acc

    def _create_Q(self,nodes):
        """
        @param nodes: a set of nodes ( a tuple containing staring point, ending point, word, and pos)
        @type nodes: list
        @return: a dict for check any two nodes whether are connected or not
        """
        Q = {0:[]}
        for i,node_i in enumerate(nodes):
            if node_i[0] == 0:
                Q[0] += [i+1]
            for j,node_j in enumerate(nodes):
                if i != j and i < j and node_i[1] == node_j[0]:
                    if i+1 not in Q:
                        Q[i+1] = [j+1]
                    else:
                        Q[i+1] += [j+1]
        return Q

    def _init_p_chart(self,P,n):
        # item = number of badness
        # initialization chart table
        for i in range(0,n+1,1):
            for j in range(i,n+1,1):
                for d in ['>','<']:
                    for c in [0,1]:
                        item = 0
                        if i not in P:
                            P[i] = {j:{d:{c:item}}}
                        elif i in P and j not in P[i]:
                            P[i][j] = {d:{c:item}}
                        elif i in P and j in P[i] and d not in P[i][j]:
                            P[i][j][d] = {c:item}
                        elif i in P and j in P[i] and d in P[i][j] and c not in P[i][j][d]:
                            P[i][j][d][c] = item
        return P

    def _init_basic_chart(self,C,n):
        # item = [[score,deps]]
        # initialization chart table
        for i in range(0,n,1):
            for j in range(i,n,1):
                for d in ['>','<']:
                    for c in [0,1]:
                        item = [(0,[])]
                        if i not in C:
                            C[i] = {j:{d:{c:item}}}
                        elif i in C and j not in C[i]:
                            C[i][j] = {d:{c:item}}
                        elif i in C and j in C[i] and d not in C[i][j]:
                            C[i][j][d] = {c:item}
                        elif i in C and j in C[i] and d in C[i][j] and c not in C[i][j][d]:
                            C[i][j][d][c] = item
        return C

    def _init_chart_trie(self,C,n,etrees):
        # item = [[score,deps,(trie_elementary_trees,attached,accept_id),traces,num_of_badness]]
        # initialization chart table
        for i in range(0,n,1):
            for j in range(i,n,1):
                for d in ['>','<']:
                    for c in [0,1]:
                        item = []
                        if i == j and i == 0:
                            item = [[0,[],('root',[],[]),[],0]]
                        elif i == j and i == n-1:
                            item = [[0,[],('end',[],[]),[],0]]
                        elif i == j and i > 0:
                            et,all_id = etrees['%d-%d'%(i,i+1)]
                            item = [[0,[],(et,[],all_id),[],0]]
                        elif i != j: 
                            item = []

                        if i not in C:
                            C[i] = {j:{d:{c:item}}}
                        elif i in C and j not in C[i]:
                            C[i][j] = {d:{c:item}}
                        elif i in C and j in C[i] and d not in C[i][j]:
                            C[i][j][d] = {c:item}
                        elif i in C and j in C[i] and d in C[i][j] and c not in C[i][j][d]:
                            C[i][j][d][c] = item
        return C

    def _assign_function(self,mst):
        results = []
        lines = mst.strip().split('\n')
        etree = mst2etree(lines)
        s_len = len(lines[0].strip().split())
        root = etree.getroot()
        results.append((int(root.getchildren()[0].get('snode').split('_')[0]),'root'))
        b_table = create_between_pos_table(lines[1].strip().split())
        compute_label(root,s_len,b_table,results,self.label_maxent_model)
        results.sort()
        labels = '\t'.join(map(lambda x:x[1],results))
        lines[2] = labels

        return '\n'.join(lines)

    def _compute_maxent_prob_by_feature(self,features):
        x,y = self.maxent_model.eval_all(features.split())
        if x[0] == 'Yes': 
            if float(x[1]) != 0:
                return math.log(float(x[1]))
            return -999
        else: 
            if float(y[1]) != 0:
                return math.log(float(y[1]))
            return -999

    def _compute_tokens_prob(self,tokens,m):
        prob = 0
        num_t = t3.get_num_tags(m)
        for i,t in enumerate(tokens):
            wp = t3.get_lexical_prob(m, t[0], t[1])
            if i == 0:
                t_i = t3.find_tag(m,tokens[i][1])
                n_index = t3.ngram_index(0,num_t,t_i,-1,-1)
            elif i == 1:
                t_i = t3.find_tag(m,tokens[i-1][1])
                t_j = t3.find_tag(m,tokens[i][1])
                n_index = t3.ngram_index(1,num_t,t_i,t_j,-1)
            else:
                t_i = t3.find_tag(m,tokens[i-2][1])
                t_j = t3.find_tag(m,tokens[i-1][1])
                t_k = t3.find_tag(m,tokens[i][1])
                n_index = t3.ngram_index(2,num_t,t_i,t_j,t_k)
            p = t3.get_transition_prob(m, n_index) + wp
            prob += p
        
        return prob

    def _get_tokens_prob(self,dep,t_mem):
        tokens = self._deps2tokens(dep)
        md5_tkey = md5.new(' '.join(map(lambda x:'%s/%s'%(x[0],x[1]),tokens))).digest()
        if md5_tkey in t_mem:
            t_prob = t_mem[md5_tkey]
        else:
            t_prob = self._compute_tokens_prob(tokens,self.trigram_model)
            t_mem[md5_tkey] = t_prob
        return t_prob

    def _get_mira_score(self,s,t,loc,dep,arrow,p_mem,b_table,mode='normal'):
        if s < 0:
            raise ParameterError(s)

        if mode == 'lattice':
            tokens = self._deps2tokens(dep)
            tags = map(lambda x:x[1],tokens)
            b_table = create_between_pos_table(tags)
        else:
            tokens = self.units

        #print s,t,tokens[s][0],tokens[s][1],tokens[t][0],tokens[t][1]
        
        txt = ' '.join(map(lambda x:'%s/%s'%(x[0],x[1]), tokens))
        pkey = md5.new('%d:%s:%s:%d'%(s,arrow,txt,t)).digest()

        if pkey in p_mem:
            p = p_mem[pkey]
        else:
            if arrow == '->':
                if mode == 'lattice':
                    f = self.mira_model._extract_features(0,len(tokens)-1,loc,tokens,b_table)
                else:
                    f = self.mira_model._extract_features(s,t,loc,tokens,b_table)
            elif arrow == '<-':
                if mode == 'lattice':
                    f = self.mira_model._extract_features(0,len(tokens)-1,loc,tokens,b_table)
                else:
                    f = self.mira_model._extract_features(s,t,loc,tokens,b_table)
            p = f.prod(self.mira_model.v)
            p_mem[pkey] = p

        return p

    def _get_deps_prob(self,s,t,loc,dep,arrow,p_mem,b_table,mode='normal'):
        if s < 0:
            raise ParameterError(s)

        if mode == 'lattice':
            tokens = self._deps2tokens(dep)
            tags = map(lambda x:x[1],tokens)
            b_table = create_between_pos_table(tags)
        else:
            tokens = self.units

        txt = ' '.join(map(lambda x:'%s/%s'%(x[0],x[1]), tokens))
        pkey = md5.new('%d:%s:%s:%d'%(s,arrow,txt,t)).digest()

        if pkey in p_mem:
            p = p_mem[pkey]
        else:
            if arrow == '->':
                if mode == 'lattice':
                    #TODO set proper start and end flag
                    f = extract_features(0,len(tokens)-1,loc,tokens,b_table,start=False,end=False)
                else:
                    f = extract_features(s,t,loc,tokens,b_table)
            elif arrow == '<-':
                if mode == 'lattice':
                    #TODO set proper start and end flag
                    f = extract_features(0,len(tokens)-1,loc,tokens,b_table,start=False,end=False)
                else:
                    f = extract_features(s,t,loc,tokens,b_table)

            p = self._compute_maxent_prob_by_feature(f)
            p_mem[pkey] = p

        return p

    def _check_conflict(self,item1,item2):
        tet = item1[0] # = item2[0]
        attached = item1[1] + item2[1]
        accept_id = list(set(item1[2]) & set(item2[2]))
        for i,key in enumerate(attached):
            r1,id1 = tet.search_key('1',key,attached[:i]+attached[i+1:],accept_id)
            r2,id2 = tet.search_key('3',key,attached[:i]+attached[i+1:],accept_id)
            if r1+r2 == []:
                return False
        return True

    def _rearrange_by_trigram(self,otmp,k_best):
        #T = 3
        if not self.use_lang_model:
            otmp.sort()
            otmp.reverse()
            return otmp[:k_best]

        tmp = []
        #ctmp = []
        for obj in otmp:
            if obj[1] == []: continue
            tokens = self._deps2tokens(obj[1])
            #if ctmp.count(tokens) < T:
            t_prob = self._compute_tokens_prob(tokens,self.trigram_model)
            tmp.append((t_prob,obj))
            #ctmp.append(tokens)
        tmp.sort()
        tmp.reverse()

        tmp2 = []
        for t_prob,obj in tmp[:k_best]:
            tmp2.append(obj)
        tmp2.sort()
        tmp2.reverse()
        return tmp2

    def _filter_by_badness(self,otmp,bad_allow=0):
        tmp = []
        for score,deps,e_obj,traces,badness in otmp:
            if badness <= bad_allow:
                tmp.append([score,deps,e_obj,traces,badness])
        tmp.sort()
        tmp.reverse()
        return tmp

    def _merge_list(self,left,right,k):
        result = []
        while len(left) > 0 and len(right) > 0 and len(result) < k:
            if left[0][0] >= right[0][0]:
                result.append(left[0])
                left = left[1:]
            else:
                result.append(right[0])
                right = right[1:]

        while len(left) > 0 and len(result) < k:
            result.append(left[0])
            left = left[1:]

        while len(right) > 0 and len(result) < k:
            result.append(right[0])
            right = right[1:]

        return result

    # if mode = normal, sequence score will be disable
    def _do_parse_lattice_trie(self,n,C,Q,acc,token_prob=False,k_best=1,mode='normal',bad_allow=0, fixed_deps=[]):
        bias = math.log(self.bias)
        b_table = None
        if mode == 'normal':
            tags = map(lambda x:x[1],self.units)
            b_table = create_between_pos_table(tags)

        is_label = False

        p_mem,t_mem = {},{}
        for k in range(1,n,1):
            for s in range(0,n,1):
                t = s + k
                if t > n-1: break

                otmp1,otmp2 = [],[]
                for r in range(s,t,1):
                    if r not in Q: continue
                    rtmp1,rtmp2 = [],[]
                    for q in Q[r]:
                        if (q < t and q in acc and t in acc[q]) or (q == t):
                            if C[s][r]['>'][1] != [] and C[q][t]['<'][1] != []:
                                kb = KBest(k_best,C[s][r]['>'][1],C[q][t]['<'][1]).mult()
                                for (score,(i,j)) in kb:
                                    cs = C[s][r]['>'][1][i]
                                    ct = C[q][t]['<'][1][j]

                                    t_s,t_t = self.T[s],self.T[t]
                                    score = cs[0] + ct[0]

                                    # part 1: s --> t
                                    if s == 0 and r == 0 and t != n-1: # connect root node
                                        dep = cs[1] + ct[1] + [(s,'',t)]
                                        p_st = 0
                                        if self.T[t] not in self.roots:
                                            p_st = bias

                                        trace = '%d:%s-s>%d:%s'%(s,cs[2][2],t,ct[2][2])
                                        trace = '%d,%d-%d,%d:>:0:(%.2f)'%(s,r,q,t,score)
                                        traces = cs[3] + ct[3] + [trace]
                                        attached = ct[2][1] + []
                                        badness = cs[4] + ct[4]
                                        rtmp1.append((score+p_st,dep,
                                            (cs[2][0],attached,cs[2][2]),traces,badness))
                                    elif q == n-1 and t == n-1: # connect ending node
                                        dep = cs[1] + ct[1] 
                                        trace = '%d:%s-e>%d:%s'%(s,cs[2][2],t,ct[2][2])
                                        trace = '%d,%d-%d,%d:>:0:(%.2f)'%(s,r,q,t,score)
                                        traces = cs[3] + ct[3] + [trace]
                                        attached = cs[2][1] + []
                                        badness = cs[4] + ct[4]
                                        rtmp1.append((score,dep,(cs[2][0],attached,cs[2][2]),traces,badness))
                                    elif s > 0:
                                        attached = cs[2][1] + [] #create new list
                                        key1,key2 = '>-c-%s-R'%(t_t),'<-a-%s-L'%(t_s)
                                        dep = cs[1] + ct[1]
                                        # compute dependencies prob
                                        if self.model_type == 'maxent':
                                            p_st = self._get_deps_prob(\
                                                s,t,'R',\
                                                dep+[(s,'',t)],\
                                                '->',p_mem,b_table,mode=mode)

                                        elif self.model_type == 'mira':
                                            p_st = self._get_mira_score(\
                                                s,t,'R',\
                                                dep+[(s,'',t)],\
                                                '->',p_mem,b_table,mode=mode)

                                        ## For adjunct, don't have to collect attached key.
                                        ## Because, the Einser'algorithm doesn't allow multiple parent
                                        r1,id1 = cs[2][0].search_key('1',key1,attached,cs[2][2])
                                        r2,id2 = cs[2][0].search_key('3',key1,attached,cs[2][2])
                                        r3,id3 = ct[2][0].search_key('2',key2,attached,ct[2][2])
                                        r4,id4 = ct[2][0].search_key('3',key2,attached,ct[2][2])
                                        if r1 != []:
                                            if not is_label:
                                                dep = cs[1] + ct[1] + [(s,'',t)]
                                            else:
                                                dep = cs[1] + ct[1] + [(s,'/'.join(list(set(r1))),t)]
                                            trace = '%d:%s-c>%d:%s'%(s,id1,t,ct[2][2])
                                            trace = '%d,%d-%d,%d:>:0:(%.2f)(%.2f)'%(s,r,q,t,score,p_st)
                                            traces = cs[3] + ct[3] + [trace]
                                            badness = cs[4] + ct[4]
                                            rtmp1.append((\
                                                score+p_st,\
                                                dep,\
                                                (cs[2][0],attached+[key1],id1),\
                                                traces,\
                                                badness))
                                        if r2 != []:
                                            if not is_label:
                                                dep = cs[1] + ct[1] + [(s,'',t)]
                                            else:
                                                dep = cs[1] + ct[1] + [(s,'/'.join(list(set(r2))),t)]
                                            trace = '%d:%s-c>%d:%s'%(s,id2,t,ct[2][2])
                                            trace = '%d,%d-%d,%d:>:0:(%.2f)(%.2f)'%(s,r,q,t,score,p_st)
                                            traces = cs[3] + ct[3] + [trace]
                                            badness = cs[4] + ct[4]
                                            rtmp1.append((\
                                                score+p_st,\
                                                dep,\
                                                (cs[2][0],attached+[key1],id2),\
                                                traces,\
                                                badness))
                                        if r3+r4 != []:
                                            if not is_label:
                                                dep = cs[1] + ct[1] + [(s,'',t)]
                                            else:
                                                dep = cs[1] + ct[1] + [(s,'/'.join(list(set(r3+r4))),t)]
                                            trace = '%d:%s-a>%d:%s'%(s,cs[2][2],t,ct[2][2])
                                            trace = '%d,%d+%d,%d:>:0:(%.2f)(%.2f)'%(s,r,q,t,score,p_st)
                                            traces = cs[3] + ct[3] + [trace]
                                            badness = cs[4] + ct[4]
                                            rtmp1.append((\
                                                score+p_st,\
                                                dep,\
                                                (cs[2][0],attached,cs[2][2]),\
                                                traces,\
                                                badness)) # no attaching for adjunct
                                        if r1+r2+r3+r4 == []:
                                            dep = cs[1] + ct[1] + [(s,'',t)]
                                            trace = '%d:%s-u>%d:%s'%(s,cs[2][2],t,ct[2][2])
                                            traces = cs[3] + ct[3] + [trace]
                                            badness = cs[4] + ct[4] + 1
                                            rtmp1.append((
                                                score+p_st+bias,\
                                                dep,\
                                                (cs[2][0],attached,cs[2][2]),\
                                                traces,\
                                                badness))
                                    
                                    # part 2: s <-- t
                                    if s > 0 and (q != n-1 or t != n-1):
                                        attached = ct[2][1] + []
                                        dep = cs[1] + ct[1]
                                        key1,key2 = '>-c-%s-L'%(t_s),'<-a-%s-R'%(t_t)

                                        if self.model_type == 'maxent':
                                            p_ts = self._get_deps_prob(
                                                s,t,'L',\
                                                dep+[(t,'',s)],\
                                                '<-',p_mem,b_table,mode=mode)
                                        elif self.model_type == 'mira':
                                            p_ts = self._get_mira_score(
                                                s,t,'L',\
                                                dep+[(t,'',s)],\
                                                '<-',p_mem,b_table,mode=mode)

                                        r1,id1 = ct[2][0].search_key('1',key1,attached,ct[2][2])
                                        r2,id2 = ct[2][0].search_key('3',key1,attached,ct[2][2])
                                        r3,id3 = cs[2][0].search_key('2',key2,attached,cs[2][2])
                                        r4,id4 = cs[2][0].search_key('3',key2,attached,cs[2][2])
                                        if r1 != []:
                                            if not is_label:
                                                dep = cs[1] + ct[1] + [(t,'',s)]
                                            else:
                                                dep = cs[1] + ct[1] + [(t,'/'.join(list(set(r1))),s)]
                                            trace = '%d:%s-c>%d:%s'%(t,id1,s,cs[2][2])
                                            trace = '%d,%d-%d,%d:<:0:(%.2f)(%.2f)'%(s,r,q,t,score,p_ts)
                                            traces = cs[3] + ct[3] + [trace]
                                            badness = cs[4] + ct[4]
                                            rtmp2.append((score+p_ts,\
                                                dep,\
                                                (ct[2][0],attached+[key1],id1),\
                                                traces,badness))
                                        if r2 != []:
                                            if not is_label:
                                                dep = cs[1] + ct[1] + [(t,'',s)]
                                            else:
                                                dep = cs[1] + ct[1] + [(t,'/'.join(list(set(r2))),s)]
                                            trace = '%d:%s-c>%d:%s'%(t,id2,s,cs[2][2])
                                            trace = '%d,%d+%d,%d:<:0:(%.2f)(%.2f)'%(s,r,q,t,score,p_ts)
                                            traces = cs[3] + ct[3] + [trace]
                                            badness = cs[4] + ct[4]
                                            rtmp2.append((score+p_ts,\
                                                dep,\
                                                (ct[2][0],attached+[key1],id2),\
                                                traces,badness))
                                        if r3+r4 != []:
                                            if not is_label:
                                                dep = cs[1] + ct[1] + [(t,'',s)]
                                            else:
                                                dep = cs[1] + ct[1] + [(t,'/'.join(list(set(r3+r4))),s)]
                                            trace = '%d:%s-a>%d:%s'%(t,ct[2][2],s,cs[2][2])
                                            trace = '%d,%d-%d,%d:<:0:(%.2f)(%.2f)'%(s,r,q,t,score,p_ts)
                                            traces = cs[3] + ct[3] + [trace]
                                            badness = cs[4] + ct[4]
                                            rtmp2.append((score+p_ts,\
                                                dep,\
                                                (ct[2][0],attached,ct[2][2]),\
                                                traces,badness)) # no attaching for adjunct
                                        if r1+r2+r3+r4 == []:
                                            dep = cs[1] + ct[1] + [(t,'',s)]
                                            trace = '%d:%s-u>%d:%s'%(t,ct[2][2],s,cs[2][2])
                                            traces = cs[3] + ct[3] + [trace]
                                            badness = cs[4] + ct[4] + 1
                                            rtmp2.append((\
                                                score+p_ts+bias,\
                                                dep,\
                                                (ct[2][0],attached,ct[2][2]),\
                                                traces,badness))

                    otmp1 = otmp1 + rtmp1
                    otmp2 = otmp2 + rtmp2

                if mode == 'lattice':
                    C[s][t]['>'][0] = self._rearrange_by_trigram(\
                        self._filter_by_badness(otmp1,bad_allow),k_best)
                    C[s][t]['<'][0] = self._rearrange_by_trigram(\
                        self._filter_by_badness(otmp2,bad_allow),k_best)
                elif mode == 'normal':
                    C[s][t]['>'][0] = self._filter_by_badness(otmp1,bad_allow)
                    C[s][t]['<'][0] = self._filter_by_badness(otmp2,bad_allow)

                #print s,t,'R',C[s][t]['>'][0][0][0]
                #print ''
                
                # part 3
                otmp,d_tmp = [],[]
                for r in range(s,t,1):
                    if (s == 0 or s == r or ( s in acc and r in acc[s] )) and ( r in acc and t in acc[r] ):
                        rtmp = []
                        if C[s][r]['<'][1] != [] and C[r][t]['<'][0] != []:
                            kb = KBest(k_best,C[s][r]['<'][1],C[r][t]['<'][0]).mult()
                            for (score,(i,j)) in kb:
                                cs = C[s][r]['<'][1][i]
                                ct = C[r][t]['<'][0][j]
                                score = cs[0] + ct[0]
                                dep = cs[1] + ct[1]
                                trace = '%d,%d-%d,%d:<:1:(%.2f)'%(s,r,r,t,score)
                                traces = cs[3] + ct[3] + [trace]
                                badness = cs[4] + ct[4]
                                attached = ct[2][1] + []
                                if dep not in d_tmp:
                                    rtmp.append((score,dep,(ct[2][0],attached,ct[2][2]),traces,badness))
                                    d_tmp.append(dep)

                        otmp = otmp + rtmp

                if mode == 'lattice':
                    C[s][t]['<'][1] = self._rearrange_by_trigram(\
                        self._filter_by_badness(otmp,bad_allow),k_best)
                elif mode == 'normal':
                    C[s][t]['<'][1] = self._filter_by_badness(otmp,bad_allow)
                                        
                # part 4
                otmp,d_tmp = [],[]
                for r in range(s+1,t+1,1):
                    if (s == 0 or (s in acc and r in acc[s] )) and (r == t or ( r in acc and t in acc[r] )):
                        rtmp = []
                        if C[s][r]['>'][0] != [] and C[r][t]['>'][1] != []:
                            kb = KBest(k_best,C[s][r]['>'][0],C[r][t]['>'][1]).mult()
                            for (score,(i,j)) in kb:
                                cs = C[s][r]['>'][0][i]
                                ct = C[r][t]['>'][1][j]
                                score = cs[0] + ct[0]
                                dep = cs[1] + ct[1]
                                trace = '%d,%d-%d,%d:>:1:(%.2f)'%(s,r,r,t,score)
                                traces = cs[3] + ct[3] + [trace]
                                badness = cs[4] + ct[4]
                                attached = cs[2][1] + []
                                if dep not in d_tmp:
                                    otmp.append((score,dep,(cs[2][0],attached,cs[2][2]),traces,badness))
                                    d_tmp.append(dep)

                        otmp = otmp + rtmp

                if mode == 'lattice':
                    C[s][t]['>'][1] = self._rearrange_by_trigram(\
                        self._filter_by_badness(otmp,bad_allow),k_best)
                elif mode == 'normal':
                    C[s][t]['>'][1] = self._filter_by_badness(otmp,bad_allow)

        results = C[0][n-1]['>'][1]
        output = ''
        if not self.multi_results and results != []:
            mst = self._decode_deps(results[0][1])
            if self.label_model_file != None:
                mst = self._assign_function(mst)
            output += mst + '\n'
        elif self.multi_results and results != []:
            for r in results:
                mst = self._decode_deps(r[1])
                if self.label_model_file != None:
                    mst = self._assign_function(mst)
                output += '%f\n'%(r[0]) + mst + '\n'
            output += '\n'
        return output

    def _do_init_parse(self, units, nodes, graph, k_best, mode, fixed_deps=[]):
        n = len(units) 
        W = map(lambda x:x[0],units)
        T = map(lambda x:x[1],units)

        self.W = W
        self.T = T

        self.units = []
        for w,t in units:
            if t == 'npn':
                self.units.append(('<npn>','npn'))
            elif t != 'npn':
                self.units.append((encode_number(w),t))

        Q = self._create_Q(nodes)
        acc = self._create_acc(nodes,graph)

        tries = {}
        for i in range(n):
            if i != 0 and i < n-1: # skip root node and ending node
                trie = TrieETrees('%s/%s'%(W[i],T[i]))
                if self.dig_file == None: 
                    all_id = trie.process_db(skip=self.excluded) # load DIG from database
                else:
                    all_id = trie.process(self.mtable,self.itable) # load DIG from file

                if all_id == [] and T[i] not in Noun+Number+Nlab+Pronoun+Conjunction:
                    #sys.__stderr__.write('relax: %s/%s\n'%(W[i],T[i]))
                    trie = TrieETrees(T[i])
                    all_id = trie.process(self.mtable,self.itable,relax=True,size=1)

                tries['%d-%d'%(i,i+1)] = (trie,all_id)

        C = {}
        self._init_chart_trie(C,n,tries)

        mst,b = '',self.bad_allow

        # if fixed_deps is used we will not use bad_allow option
        if len(fixed_deps) > 0:
            b = n

        while mst.strip() == '':
            #sys.__stderr__.write('trying bad_allow = %d\n'%(b))
            mst = self._do_parse_lattice_trie(n,C,Q,acc,token_prob=True,k_best=k_best,mode=mode,bad_allow=b, fixed_deps=fixed_deps)
            b += 1
        return mst

    def _do_parse_mira_tagged_text(self,C,Sc,n,k_best):
        tags = map(lambda x:x[1],self.units)
        b_table = create_between_pos_table(tags)
        for k in range(1,n,1):
            for s in range(0,n,1):
                t = s + k
                if t >= n: break

                p_st = Sc['%d-%d-R'%(s,t)]
                p_ts = Sc['%d-%d-L'%(s,t)]

                otmp1,otmp2 = [],[]
                for r in range(s,t,1):
                    if C[s][r]['>'][1] != [] and C[r+1][t]['<'][1] != []:
                        rtmp1,rtmp2 = [],[]
                        kb = KBest(k_best,C[s][r]['>'][1],C[r+1][t]['<'][1]).mult()
                        for (score,(i,j)) in kb:
                            cs = C[s][r]['>'][1][i]
                            ct = C[r+1][t]['<'][1][j]

                            # part 1
                            if s > 0 or (s == 0 and r == 0):
                                deps = cs[1] + ct[1] + [(s,'',t)]
                                rtmp1.append((score+p_st,deps))

                            # part 2
                            if s > 0:
                                deps = cs[1] + ct[1] + [(t,'',s)]
                                rtmp2.append((score+p_ts,deps))

                        otmp1 = self._merge_list(otmp1,rtmp1,k_best)
                        otmp2 = self._merge_list(otmp2,rtmp2,k_best)

                C[s][t]['>'][0] = otmp1
                C[s][t]['<'][0] = otmp2
                #print s,t,C[s][t]['>'][0][0][0]
                #print ''

                # part 3
                otmp = []
                for r in range(s,t,1):
                    if C[s][r]['<'][1] != [] and C[r][t]['<'][0] != []:
                        rtmp = []
                        kb = KBest(k_best,C[s][r]['<'][1],C[r][t]['<'][0]).mult()
                        for (score,(i,j)) in kb:
                            cs = C[s][r]['<'][1][i]
                            ct = C[r][t]['<'][0][j]
                            deps = cs[1] + ct[1]
                            rtmp.append((score,deps))
                        otmp = self._merge_list(otmp,rtmp,k_best)
                C[s][t]['<'][1] = otmp

                # part 4
                otmp = []
                for r in range(s+1,t+1,1):
                    if C[s][r]['>'][0] != [] and C[r][t]['>'][1] != []:
                        rtmp = []
                        kb = KBest(k_best,C[s][r]['>'][0],C[r][t]['>'][1]).mult()
                        for score,(i,j) in kb:
                            cs = C[s][r]['>'][0][i]
                            ct = C[r][t]['>'][1][j]
                            deps = cs[1] + ct[1]
                            rtmp.append((score,deps))
                        otmp = self._merge_list(otmp,rtmp,k_best)
                C[s][t]['>'][1] = otmp

        results = C[0][n-1]['>'][1]
        tmp = []
        for result in results:
            result_deps = result[1]
            tmp += [result_deps]
        return tmp

    def _do_parse_basic_tagged_text(self,C,n,fixed_deps=[]): # do not use DIGs
        tags = map(lambda x:x[1],self.units)
        b_table = create_between_pos_table(tags)
        for k in range(1,n,1):
            for s in range(0,n,1):
                t = s + k
                if t >= n: break

                if (s,t) in fixed_deps:
                    p_st = 9999
                else:
                    f_st = extract_features(s,t,'R',self.units,b_table)
                    p_st = self._compute_maxent_prob_by_feature(f_st)

                if (t,s) in fixed_deps:
                    p_ts = 9999
                else:
                    f_ts = extract_features(s,t,'L',self.units,b_table)
                    p_ts = self._compute_maxent_prob_by_feature(f_ts)

                # part 1
                otmp = []
                for r in range(s,t,1):
                    cs = C[s][r]['>'][1][0]
                    ct = C[r+1][t]['<'][1][0]
                    if s==0 and r==0: # find root
                        score = cs[0] + ct[0] + p_st
                        deps = cs[1] + ct[1] + [(s,'',t)]
                        otmp.append((score,deps))
                    elif s > 0:
                        score = cs[0] + ct[0] + p_st # cs.score + ct.score
                        deps = cs[1] + ct[1] + [(s,'',t)]
                        otmp.append((score,deps))
                otmp.sort()
                otmp.reverse()
                if otmp != []:
                    C[s][t]['>'][0] = otmp[:1]

                # part 2
                otmp = []
                for r in range(s,t,1):
                    cs = C[s][r]['>'][1][0]
                    ct = C[r+1][t]['<'][1][0]
                    if s > 0:# and (r+1 != n or t != n):
                        score = cs[0] + ct[0] + p_ts # cs.score + ct.score
                        deps = cs[1] + ct[1] + [(t,'',s)]
                        otmp.append((score,deps))
                otmp.sort()
                otmp.reverse()
                if otmp != []:
                    C[s][t]['<'][0] = otmp[:1]

                # part 3
                otmp = []
                for r in range(s,t,1):
                    cs = C[s][r]['<'][1][0]
                    ct = C[r][t]['<'][0][0]
                    score = cs[0] + ct[0]
                    deps = cs[1] + ct[1]
                    otmp.append((score,deps))
                otmp.sort()
                otmp.reverse()
                if otmp != []:
                    C[s][t]['<'][1] = otmp[:1]

                # part 4
                otmp = []
                for r in range(s+1,t+1,1):
                    cs = C[s][r]['>'][0][0]
                    ct = C[r][t]['>'][1][0]
                    score = cs[0] + ct[0]
                    deps = cs[1] + ct[1]
                    otmp.append((score,deps))
                otmp.sort()
                otmp.reverse()
                if otmp != []:
                    C[s][t]['>'][1] = otmp[:1]
        if not self.multi_results:
            result = C[0][n-1]['>'][1][0]
            result_deps = result[1]
            return self._decode_deps(result_deps)
        else:
            output = ''
            for r in C[0][n-1]['>'][1]:
                output += self._decode_deps(r[1]) + '\n'
            return output

    def _etrees2tokens(self,etrees):
        tokens = []
        for i in range(len(etrees)):
            if etrees[i].word != 'root' and etrees[i].word != 'end':
                tokens.append((etrees[i].word,etrees[i].tag))
        return tokens

    def _deps2tokens(self,deps):
        tmp,tokens = [],[]
        for s,roles,t in deps:
            tmp.append(s)
            tmp.append(t)
        tmp = list(set(tmp))
        tmp.sort()
        for i in tmp:
            if i > 0:
                tokens.append(self.units[i])
        return tokens

    def _decode_traces(self,traces):
        output = ''
        def _merge(rule,order):
            out = ''
            rule = map(str.strip,rule.split('-->'))
            order = map(str.strip,order.split('-->'))
            for i in range(len(rule)):
                if i < len(rule)-1:
                    out += '%s:(%s) -->'%(rule[i],order[i])
                else:
                    out += '%s:(%s)'%(rule[i],order[i])
            return out
        for trace in traces:
            x,r,y = re.match('(.+)-([acseu])\>(.+)',trace).groups()
            s,sid = x.split(':')
            sid = sid.strip(']').strip('[').split(',')
            t,tid = y.split(':')
            tid = tid.strip(']').strip('[').split(',')
            if sid[0] == '' or tid[0] == '': continue
            output += '%s %s %s %s %s\n'%(self.W[int(s)-1],self.T[int(s)-1],'-%s->'%(r),self.W[int(t)-1],self.T[int(t)-1])
            stmp = []
            max_s = 0
            for id in sid:
                index_obj = DigIndex.selectBy(id=int(id))[0]
                m =  _merge(index_obj.digrule.rule,index_obj.word_order)
                if len(m) > max_s:
                    max_s = len(m)
                stmp.append(m)
            ttmp = []
            for id in tid:
                index_obj = DigIndex.selectBy(id=int(id))[0]
                m =  _merge(index_obj.digrule.rule,index_obj.word_order)
                ttmp.append(m)

            if len(stmp) > len(ttmp):
                d = len(stmp)-len(ttmp)
                fd = (d/2) + d%2
                bd = d/2
                for i in range(fd):
                    ttmp.insert(0,'')
                for i in range(bd):
                    ttmp.append('')
            else:
                d = len(ttmp)-len(stmp)
                fd = (d/2) + d%2
                bd = d/2
                for i in range(fd):
                    stmp.insert(0,'')
                for i in range(bd):
                    stmp.append('')
            for i in range(len(stmp)):
                output += stmp[i]+' '
                for j in range(max_s-len(stmp[i])):
                    output += ' '
                output += ttmp[i]+'\n'
            output += '\n\n'
        return output

    def _decode_deps(self,deps):
        tmp = []
        h_table,r_table = {},{}
        for s,role,t in deps:
            if s not in tmp:
                tmp.append(s)
            if t not in tmp:
                tmp.append(t)
            h_table[t] = s
            r_table[t] = role
        tmp.sort()
        i_map = {}
        for i,x in enumerate(tmp):
            i_map[x] = i
        W,T,H,R = [],[],[],[]

        keys = h_table.keys()
        keys.sort()
        for t in keys:
            W.append(self.W[t])
            T.append(self.T[t])
            H.append(i_map[h_table[t]])
            if H[-1] == 0:
                R.append('root')
            elif r_table[t].strip() != '':
                R.append(r_table[t])
            else:
                R.append('-')

        return '\t'.join(W) + '\n' + '\t'.join(T) + '\n' + '\t'.join(R) + '\n' + '\t'.join(map(str,H)) + '\n'

    def parse_mira_tagged_text(self, text, Sc, k_best, format='acopost'):
        W,T = ['<root>'],['<root-POS>']
        self.units = [(W[0],T[0])]

        if format == 'acopost':
            tokens = text.split()
            W = W + [w for (i,w) in enumerate(tokens) if i%2 == 0]
            T = W + [t for (i,t) in enumerate(tokens) if i%2 == 1]
            units = [(encode_number(tokens[i]),tokens[i+1]) for i in range(len(tokens)) if i%2 == 0]
        elif format == 'naist':
            units = []
            for token in text.split():
                p = token.rfind('/')
                w,t = token[:p],token[p+1:]
                units.append((encode_number(w),t))
                W.append(w)
                T.append(t)
        else:
            raise UnknownArgumentError(format,['naist','acopost'])

        for w,t in units:
            if t == 'npn':
                self.units.append(('<npn>','npn'))
            else:
                self.units.append((w,t))    

        self.W = W
        self.T = T


        C = {}
        n = len(self.units)
        self._init_basic_chart(C,n)

        return self._do_parse_mira_tagged_text(C,Sc,n,k_best=k_best)

    def parse_basic_tagged_text(self, text, format='acopost', fixed_deps=[]):
        W,T = ['<root>'],['<root-POS>']
        self.units = [(W[0],T[0])]

        if format == 'acopost':
            tokens = text.split()
            W = W + [w for (i,w) in enumerate(tokens) if i%2 == 0]
            T = T + [t for (i,t) in enumerate(tokens) if i%2 == 1]
            units = [(encode_number(tokens[i]),tokens[i+1]) for i in range(len(tokens)) if i%2 == 0]
        elif format == 'naist':
            units = []
            for token in text.split():
                p = token.rfind('/')
                w,t = token[:p],token[p+1:]
                units.append((encode_number(w),t))
                W.append(w)
                T.append(t)
        else:
            raise UnknownArgumentError(format,['naist','acopost'])

        for w,t in units:
            if t == 'npn':
                self.units.append(('<npn>','npn'))
            else:
                self.units.append((w,t))    

        self.W = W
        self.T = T

        C = {}
        n = len(self.units)
        self._init_basic_chart(C,n)
        return self._do_parse_basic_tagged_text(C,n,fixed_deps)


    def parse_raw_text(self, text, k_best=1):
        pairs = self.tb.pre_segment(text)
        graph = self.tb.map_dict(self.dict_file,pairs,text)
        graph = self.tb.expand_unknown_words(graph,text)
        self.tb.remove_useless_syllables(graph,self.dict_file,text)
        nodes,units = [],[]

        units.append(('<root>','<root-POS>'))
        for s,t,score in graph.edges():
            word = text[s:t]
            tags = guess_pos(word,self.pos_table)
            for pos in tags:
                nodes.append((s,t,word,pos))
                units.append((word,pos))
        e = graph.edges()[-1]
        graph.add_edge(e[1],e[1]+3) # for ending node: -E- 
        nodes.append((e[1],e[1]+3,'-E-','-E-'))
        units.append(('-E','-E-'))
        return self._do_init_parse(units, nodes, graph, k_best, 'lattice')

    # use trie to store DIGs of each lexical node
    def parse_untagged_text(self, text, k_best=1):
        graph = MyXGraph()
        nodes,units = [],[]
        s = 0
        words = text.split()
        words.append('-E-') # add ending dummy node

        units.append(('<root>','<root-POS>'))
        for i,word in enumerate(words):
            t = s+len(word)
            graph.add_edge(s,t)
            if i < len(words)-1:
                tags = guess_pos(word,self.pos_table)
                for pos in tags:
                    nodes.append((s,t,word,pos))
                    units.append((word,pos))
            else: # add ending node
                nodes.append((s,t,'-E-','-E-'))
                units.append(('-E-','-E-'))
            s = t
        return self._do_init_parse(units, nodes, graph, k_best, 'lattice')

    # use trie to store DIGs of each lexical node
    def parse_tagged_text(self, text, k_best=1, fixed_deps=[]):
        graph = MyXGraph()
        nodes,units = [],[]
        s = 0
        units.append(('<root>','<root-POS>'))
        tokens = text.strip().split()
        for token in tokens:
            p = token.rfind('/')
            word = token[:p]
            pos = token[p+1:]
            graph.add_edge(s,s+1)
            nodes.append((s,s+1,word,pos))
            units.append((word,pos))
            s += 1
        nodes.append((s,s+1,'-E-','-E-'))
        units.append(('-E-','-E-'))

        # fixed_deps format = [(s1,t1), (s2,t2), ...]
        return self._do_init_parse(units, nodes, graph, k_best, 'normal', fixed_deps=fixed_deps)

