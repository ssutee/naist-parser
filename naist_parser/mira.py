#!/usr/bin/python2.5
import re,sys,math,cPickle,md5
from common_utils import get_simplified_pos, all_pos, all_simplified_pos, encode_number
from maxent_utils import create_between_pos_table
from cvxopt.base import spmatrix,spdiag,matrix,sparse
from cvxopt import solvers
#from numpy import diag, matrix
#from scikits.openopt import QP

class Features(list):
    def __init__(self):
        list.__init__(self)

    def prod(self,weight):
        result = 0.0
        for f in self:
            result += weight[int(f)]
        return result

class TrainingFeatures:
    def __init__(self):
        self.table = {}
        self.fid = 0

    def add(self,id,items):
        if None in items:
            return
        for item in items:
            key = str(id)+':'+'/'.join(item)
            md5_key = md5.new(key).hexdigest()
            if md5_key not in self.table:
                self.table[md5_key] = self.fid
                self.fid += 1

    def find(self,key):
        return self.table.get(key,None)

    def get_size(self):
        return self.fid

class TestingFeatures:
    def __init__(self,training_features):
        self.features = []
        self.training_features = training_features

    def add(self,id,items):
        if None in items:
            return
        for item in items:
            key = str(id)+':'+'/'.join(item)
            md5_key = md5.new(key).hexdigest()
            self.features.append(md5_key)

    def to_vector(self):
        tmp = Features()
        for f in self.features:
            id = self.training_features.find(f)
            if id != None: 
                tmp.append(id)
        return tmp

class FeaturesModel:
    def __init__(self,mode):
        self.training_features = TrainingFeatures()
        self.mode = mode

    def get_size_of_features(self):
        return self.training_features.get_size()

    def _analyze_values(self,i,j,tags):
        """ i is a small number
            j is a large number
        """
        ti = tags[i]
        tj = tags[j]
        si = get_simplified_pos(ti)
        sj = get_simplified_pos(tj)

        dt = abs(i-j)-1
        if dt >= 5: dt = 5
        if dt >= 10: dt = 10
        if dt >= 15: dt = 15
        dt = str(dt)

        if i == 0: 
            tpi,spi = '-S-','-S-'
        else:
            tpi = tags[i-1]
            spi = get_simplified_pos(tpi)

        if j == len(tags)-1: 
            tnj,snj = '-E-','-E-'
        else:
            tnj = tags[j+1]
            snj = get_simplified_pos(tnj)

        if i != j-1:
            tni = tags[i+1]
            sni = get_simplified_pos(tni)
            tpj = tags[j-1]
            spj = get_simplified_pos(tpj)
        else:
            tni,sni = '-M-','-M-'
            tpj,spj = '-M-','-M-'

        return si,sj,dt,tpi,tni,tpj,tnj,spi,sni,spj,snj


    def _add_features_to(self,obj,i,j,words,tags,di,b_table):

        def add_features(features,obj):
            for i,f in enumerate(features):
                obj.add(i,f)

        wi,wj = words[i],words[j]
        ti,tj = tags[i],tags[j]

        si,sj,dt,tpi,tni,tpj,tnj,spi,sni,spj,snj = self._analyze_values(i,j,tags)

        t_tags,s_tags = [],[]
        if '%d-%d'%(i,j) in b_table:
            t_tags = b_table['%d-%d'%(i,j)]
            t_tags = list(set(t_tags))
            s_tags = map(get_simplified_pos,list(t_tags))
            s_tags = list(set(s_tags))

        # feature posR posMid posL
        ttmp1,ttmp2, = [],[]
        for tm in t_tags:
            ttmp1.append([ti,tm,tj])
            ttmp2.append([ti,tm,tj,di,dt])

        stmp1,stmp2, = [],[]
        for sm in s_tags:
            stmp1.append([si,sm,sj])
            stmp2.append([si,sm,sj,di,dt])
            
        # between POS
        bt_t = (ttmp1,ttmp2)
        bt_st = (stmp1,stmp2)


        if di == 'R':
            wh,wc = wi,wj
            th,tc = ti,tj
            sh,sc = si,sj
        elif di == 'L':
            wh,wc = wj,wi
            th,tc = tj,ti
            sh,sc = sj,si
            
        # Unigram features
        unigram = (
            [[wh]],
            [[wc]],
            [[th]],
            [[tc]],
            [[sh]],
            [[sc]],
            [[wh,th]],
            [[wc,tc]],
            [[wh,sh]],
            [[wc,sc]],

            [[wh,di,dt]],
            [[wc,di,dt]],
            [[th,di,dt]],
            [[tc,di,dt]],
            [[sh,di,dt]],
            [[sc,di,dt]],
            [[wh,th,di,dt]],
            [[wc,tc,di,dt]],
            [[wh,sh,di,dt]],
            [[wc,sc,di,dt]],
        )
        bigram = (
            [[wh,wc]],
            [[th,tc]],
            [[sh,sc]],
            [[th,wc,tc]],
            [[wh,wc,tc]],
            [[wh,th,tc]],
            [[sh,wc,sc]],
            [[wh,wc,sc]],
            [[wh,sh,sc]],
            [[wh,sh,wc]],
            [[wh,th,wc,tc]],
            [[wh,sh,wc,sc]],

            [[wh,wc,di,dt]],
            [[th,tc,di,dt]],
            [[sh,sc,di,dt]],
            [[th,wc,tc,di,dt]],
            [[wh,wc,tc,di,dt]],
            [[wh,th,tc,di,dt]],
            [[sh,wc,sc,di,dt]],
            [[wh,wc,sc,di,dt]],
            [[wh,sh,sc,di,dt]],
            [[wh,sh,wc,di,dt]],
            [[wh,th,wc,tc,di,dt]],
            [[wh,sh,wc,sc,di,dt]],
        )
        surround_t = (
            [[ti,tni,tpj,tj]], # Ti/Ti+1/Tj-1/Tj
            [[tpi,ti,tpj,tj]], # Ti-1/Ti/Tj-1/Tj
            [[ti,tni,tj,tnj]], # Ti/Ti+1/Tj/Tj+1
            [[tpi,ti,tj,tnj]], # Ti-1/Ti/Tj/Tj+1
            [[tpi,ti]],        # Ti-1/Ti
            [[ti,tni]],        # Ti/Ti+1
            [[tpi,ti,tni]],    # Ti-1/Ti/Ti+1
            [[tpj,tj]],        # Tj-1/Tj
            [[tj,tnj]],        # Tj/Tj+1
            [[tpj,tj,tnj]],    # Tj-1/Tj/Tj+1

            [[ti,tni,tpj,tj,di,dt]], # Ti/Ti+1/Tj-1/Tj
            [[tpi,ti,tpj,tj,di,dt]], # Ti-1/Ti/Tj-1/Tj
            [[ti,tni,tj,tnj,di,dt]], # Ti/Ti+1/Tj/Tj+1
            [[tpi,ti,tj,tnj,di,dt]], # Ti-1/Ti/Tj/Tj+1
            [[tpi,ti,di,dt]],        # Ti-1/Ti
            [[ti,tni,di,dt]],        # Ti/Ti+1
            [[tpi,ti,tni,di,dt]],    # Ti-1/Ti/Ti+1
            [[tpj,tj,di,dt]],        # Tj-1/Tj
            [[tj,tnj,di,dt]],        # Tj/Tj+1
            [[tpj,tj,tnj,di,dt]],    # Tj-1/Tj/Tj+1
        )
        surround_st = (
            [[si,sni,spj,sj]],
            [[spi,si,spj,sj]],
            [[si,sni,sj,snj]],
            [[spi,si,sj,snj]],
            [[spi,si]],        
            [[si,sni]],        
            [[spi,si,sni]],    
            [[spj,sj]],        
            [[sj,snj]],        
            [[spj,sj,snj]],     

            [[si,sni,spj,sj,di,dt]],
            [[spi,si,spj,sj,di,dt]],
            [[si,sni,sj,snj,di,dt]],
            [[spi,si,sj,snj,di,dt]],
            [[spi,si,di,dt]],        
            [[si,sni,di,dt]],        
            [[spi,si,sni,di,dt]],    
            [[spj,sj,di,dt]],        
            [[sj,snj,di,dt]],        
            [[spj,sj,snj,di,dt]],     
        )
        features = unigram +\
                    bigram +\
                    surround_t +\
                    surround_st + \
                    bt_t + \
                    bt_st

        add_features(features,obj)

    def convert_data(self,i,j,words,tags,di,b_table):
        """ Convert data to features vector
        """
        testing_features = TestingFeatures(self.training_features)
        self._add_features_to(testing_features,i,j,words,tags,di,b_table)
        return testing_features.to_vector()

    def insert_data(self,i,j,words,tags,di,b_table):
        self._add_features_to(self.training_features,i,j,words,tags,di,b_table)

class MIRA:
    def __init__(self,mode='normal'):
        self._training_data = []
        self._f_model = FeaturesModel(mode)
        self.features_size = 0
        self.v = None

    def save_model(self,file_name='mira.model'):
        import bz2,struct
        output = bz2.BZ2File(file_name+'.f','w')
        for k,v in self._f_model.training_features.table.items():
            output.write('%s %d\n'%(k,v)) 
        output.close()

        norm = 0
        for i in range(self.features_size):
            norm += math.pow(self.v[i],2)
        norm = math.sqrt(norm)

        output = open(file_name+'.b','wb')
        for i in range(self.features_size):
            output.write(struct.pack('f',self.v[i]/norm))
        output.close

    def load_model(self,file_name):
        import bz2,struct
        sys.__stderr__.write('Loading model...\n')
        input = bz2.BZ2File(file_name+'.f','r')
        for line in input.readlines():
            k,v = line.strip().split()
            self._f_model.training_features.table[k] = int(v)
        input.close()
        self._f_model.training_features.fid = len(self._f_model.training_features.table)

        self.features_size = self._f_model.get_size_of_features()
        sys.__stderr__.write('%d features are loaded\n'%(self.features_size))

        input = open(file_name+'.b','rb')
        w = []
        while True:
            f = input.read(4)
            if not f:
                break
            w.append(struct.unpack('f',f)[0])
        input.close()

        self.v = spmatrix(0,[0],[0],(len(w),1))
        for i,f in enumerate(w):
            if f != 0:
                self.v[i] = f
        sys.__stderr__.write('weight vector (%d) are loaded\n'%(len(w)))

    def read_training_file(self,input_file):
        lines = open(input_file).readlines()
        print 'Reading Training Data...'
        total = 0
        # save words and tags
        tmp = []
        for line in lines:
            if line.strip() != '':
                tmp.append(line.strip())
            else:
                W = tmp[0].strip().split('\t')
                if len(W) < 2:
                    tmp = []
                    continue
                W = ['<root>'] + map(lambda x: x.strip().replace(' ','_'),W)
                T = ['<root-POS>'] + tmp[1].strip().split('\t')
                A = ['<no-type>'] + tmp[2].strip().split('\t')
                H = [-1] + map(int,tmp[3].strip().split('\t'))

                for i,w in enumerate(W):
                    if T[i] == 'npn':
                        W[i] = '<npn>'
                    else:
                        W[i] = encode_number(w)

                self._training_data.append((W,T,A,H))
                b_table = create_between_pos_table(T)
                total += 1
                if total % 10 == 0: print total

                for j,i in enumerate(H):
                    if i == -1: continue
                    if i > j:
                        self._f_model.insert_data(j,i,W,T,'L',b_table)
                    else:
                        self._f_model.insert_data(i,j,W,T,'R',b_table)

                tmp = []
        self.features_size = self._f_model.get_size_of_features()
        print total
        print 'Number of Features:',self.features_size

        self._create_features_instance()

    def _create_F(self,W,T):
        b_table = create_between_pos_table(T)
        F = {}
        for i in range(len(W)):
            for j in range(i+1,len(W),1):
                for di in ['L','R']:
                    F['%d-%d-%s'%(i,j,di)] = self._f_model.convert_data(i,j,W,T,di,b_table)
        return F

    def _extract_features(self,s,t,di,tokens,b_table):
        W,T = [],[]
        for w,p in tokens:
            W.append(w)
            T.append(p)
        return self._f_model.convert_data(s,t,W,T,di,b_table)

    def _create_Sc(self,W,T,F,Wc):
        Sc = {}
        for i in range(len(W)):
            for j in range(i+1,len(W),1):
                for di in ['L','R']:
                    Sc['%d-%d-%s'%(i,j,di)] = F['%d-%d-%s'%(i,j,di)].prod(Wc)
                    #print i,j,di,W[i],T[i],W[j],T[j],Sc['%d-%d-%s'%(i,j,di)]
        return Sc

    def _create_features_instance(self):
        self.features_instance = []
        i = 0
        for W,T,A,H in self._training_data:
            F = self._create_F(W,T)
            self.features_instance.append(F)
            i += 1
            print 'Create Features Instance: %d'%(i)

    def train(self,N=1,k=1):
        from dig_parser import DIGParser
        self._dig_parser = DIGParser()
        Q = spdiag([2]*self.features_size)
        G = spmatrix(0,[0],[0],(k,self.features_size))
        Wc = spmatrix(0,[0],[0],(self.features_size,1))
        self.v = spmatrix(0,[0],[0],(self.features_size,1))
        complete = N * len(self._training_data)
        round = 0
        for loop in range(N):
            for tid,(W,T,A,H) in enumerate(self._training_data):
                round += 1
                print 'round %d/%d'%(round,complete)
                F = self.features_instance[tid]
                gold_deps,gold_features = [],Features()
                for c,h in enumerate(H):
                    if h != -1:
                        gold_deps.append((h,c))
                        if h > c:
                            gold_features += F['%d-%d-L'%(c,h)]
                        else:
                            gold_features += F['%d-%d-R'%(h,c)]
                gold_deps.sort()

                print 'creating score table...'
                Sc = self._create_Sc(W,T,F,Wc)

                text = []
                for i in range(1,len(W),1):
                    text.append('%s/%s'%(W[i],T[i]))
                text = ' '.join(text)
                print 'input length = %d'%(len(W))
                print 'parsing %d best...'%(k)
                trees = self._dig_parser.parse_mira_tagged_text(text,Sc,k,format='naist')

                n_trees = len(trees)
                if n_trees < k:
                    for j in range(k-n_trees):
                        trees.append(trees[-1])
                        
                print 'updating weight...'
                Wc = self._update_weight(Q,G,Wc,F,gold_deps,gold_features,trees)
                self.v = self.v + Wc
                print 'done\n'

    def _loss_score(self,t1,t2):
        if len(t1) != len(t2):
            print 'error: two trees mismatch'
            sys.exit(1)

        return 1.0*len(set(t2)-set(t1))

    def _update_weight(self,Q,G,Wc,F,gold_deps,gold_features,trees):
        constraints,L = [],[]
        print 'creating constraints...'
        for i,tree in enumerate(trees):
            print '\tfor tree %d'%(i)
            deps = map(lambda x:(x[0],x[2]), tree)
            deps.sort()
            L += [-self._loss_score(gold_deps,deps)]
            fc = []
            for s,x,t in tree:
                if s > t:
                    fc += F['%d-%d-L'%(t,s)]
                else:
                    fc += F['%d-%d-R'%(s,t)]
                    
            fg = [] 
            for f in gold_features:
                if f in fc:
                    fc.remove(f)
                else:
                    fg.append(f)
            constraints += map(lambda x:(fg.count(x),i,x),fg)
            constraints += map(lambda x:(-fc.count(x),i,x),fc)
        
        print 'preparing parameters...'
        G = sparse(G*0)
        for s,i,j in constraints:
            G[(i,j)] = -s
        h = matrix(L)
        p = matrix(-2*Wc)
        sol = solvers.qp(Q,p,G,h)
        Wn = sparse(sol['x'])
        print L
        sg = gold_features.prod(Wn)
        for tree in trees:
            fc = Features()
            for s,x,t in tree:
                if s > t:
                    fc += F['%d-%d-L'%(t,s)]
                else:
                    fc += F['%d-%d-R'%(s,t)]
            sc = fc.prod(Wn)
            print sg,'-',sc,'=',sg-sc

        return Wn

