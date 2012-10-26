#!/usr/bin/python2.5
# coding=utf8

from common_utils import Complement, Adjunct
from dig_model import *

class TETree:
    def __init__(self,type,id):
        self.type = type
        self.id = id
        self.waiting_nodes = []

    def set_waiting_nodes(self,nodes):
        for n in nodes:
            self.waiting_nodes.append(n)

    def add_waiting_node(self,node):
        self.waiting_nodes.append(node)

    def match_node(self,node):
        self.waiting_nodes.remove(node)

    # if the key can be attached to the node return True, otherwise False.
    def check_attach(self,key,attached,accept_id):
        #if self.id not in accept_id:
        #    return False
        tmp1,tmp2 = [],[]
        for n in attached: #duplicate attached
            tmp1.append(n)
        for n in self.waiting_nodes:
            if n in tmp1:
                tmp1.remove(n)
            else:
                tmp2.append(n)
        if key in tmp2:
            return True
        return False

    def __repr__(self):
        return 'id:%d,w:%s'%(self.id,str(self.waiting_nodes))

class TrieETrees:
    def __init__(self,root):
        self.root = root
        self.children = {}

    def __repr__(self):
        text = ''
        for type in self.children:
            text += '\n\t%s'%(type)
            for key in self.children[type]:
                text += '\n\t\t%s'%(key)
                for tetree in self.children[type][key]:
                    text += '\n\t\t\t%s'%(tetree)
        return '%s : %s'%(self.root,text)

    def search_key(self,t_type,key,attached,accept_id):
        roles = []
        results = []
        tmp_id = []
        if t_type in self.children:
            check_key = False
            if key[0] == '>': # complement
                for c in Complement:
                    if c+':'+key in self.children[t_type]:
                        check_key = True
                        roles.append(c)
            elif key[0] == '<': # adjunct
                for a in Adjunct:
                    if a+':'+key in self.children[t_type]:
                        check_key = True
                        roles.append(a)
            if check_key:
                for role in roles:
                    for et in self.children[t_type][role+':'+key]:
                        if et.check_attach(role+':'+key,attached,accept_id):
                            results.append(role)
                            tmp_id.append(et.id)
        return results,tmp_id

    ## unit = word[pos@role] | [pos@role] | word[pos] | [pos]
    def _process_unit(self,unit):
        word,pos,role = None,None,None

        if '@' in unit and unit[0] == '[': # [pos@role]
            pos,role = unit.strip('[').strip(']').split('@')
        elif '@' in unit and unit[0] != '[': # word[pos@role]
            p = unit.find('[')
            word = unit[:p]
            pos,role = unit[p+1:].strip('[').strip(']').split('@')
        elif '@' not in unit and unit[0] == '[': # [pos]
            pos = unit.strip('[').strip(']')
        elif '@' not in unit and unit[0] != '[': # word[pos]
            p = unit.find('[')
            word = unit[:p]
            pos = unit[p+1:]
        
        return word,pos,role

    def process_db(self,skip=[]):
        all_id = []
        my_strip = lambda x:x.strip('[').strip(']')

        # process Type-I tree
        for head_obj in DigHead.selectBy(head=self.root,type='I'):
            for rule_obj in head_obj.rules:
                h,c = rule_obj.rule.split(' --> ')
                c = map(my_strip,c.split(','))
                h = my_strip(h)
                mix_r = []
                c_tmp = []
                for index_obj in rule_obj.indexes:
                    tree_id = map(lambda x:int(x.tree_number),index_obj.dig_trees)
                    if len(set(tree_id) - set(skip)) == 0: # skip the trees which are in testing data
                        continue
                    tmp = []
                    h_i,c_i = index_obj.word_order.split(' --> ')
                    h_i = int(h_i)
                    c_i = map(int,c_i.split(','))
                    for i,x in enumerate(c_i):
                        pos,role = c[i],'c'
                        if '@' in c[i]:
                            pos,role = c[i].split('@')
                        if x < h_i:
                            tmp.append('%s:>-%s-%s-%s'%(role,'c',pos,'L'))
                        else:
                            tmp.append('%s:>-%s-%s-%s'%(role,'c',pos,'R'))
                    if tmp not in c_tmp:
                        c_tmp.append(tmp)
                        mix_r.append((tmp,index_obj.id))
                for m_r,id in mix_r:
                    etree = TETree('1',id)
                    all_id.append(id)
                    for l in m_r:
                        etree.set_waiting_nodes([l])
                        if '1' not in self.children:
                            self.children['1'] = {l:[etree]}
                        elif '1' in self.children and l not in self.children['1']:
                            self.children['1'][l] = [etree]
                        elif '1' in self.children and l in self.children['1'] and etree not in self.children['1'][l]:
                            self.children['1'][l].append(etree)
                    
        # process Type-II tree
        for head_obj in DigHead.selectBy(head=self.root,type='II'):
            for rule_obj in head_obj.rules:
                h,c = map(my_strip,rule_obj.rule.split(' --> '))
                pos,role = c,'a'
                if '@' in c:
                    pos,role = c.split('@')
                mix_r = []
                c_tmp = []
                for index_obj in rule_obj.indexes:
                    h_i,c_i = map(int,index_obj.word_order.split(' --> '))
                    if h_i > c_i:
                        k = '%s:<-%s-%s-%s'%(role,'a',h,'R')
                        if k not in c_tmp:
                            c_tmp.append(k)
                            mix_r.append((k,index_obj.id))
                    else:
                        k = '%s:<-%s-%s-%s'%(role,'a',h,'L')
                        if k not in c_tmp:
                            c_tmp.append(k)
                            mix_r.append((k,index_obj.id))
                for m_r,id in mix_r:
                    etree = TETree('2',id)
                    all_id.append(id)
                    etree.set_waiting_nodes([m_r])
                    if '2' not in self.children:
                        self.children['2'] = {m_r:[etree]}
                    elif '2' in self.children and m_r not in self.children['2']:
                        self.children['2'][m_r] = [etree]
                    elif '2' in self.children and m_r in self.children['2'] and etree not in self.children['2'][m_r]:
                        self.children['2'][m_r].append(etree)

        # process Type-III tree
        for head_obj in DigHead.selectBy(head=self.root,type='III'):
            for rule_obj in head_obj.rules:
                h,c,sc = map(my_strip,rule_obj.rule.split(' --> '))
                h,c = my_strip(h),my_strip(c)
                pos,role = c,'a'
                if '@' in c:
                    pos,role = c.split('@')
                sc = map(my_strip,sc.split(','))
                mix_r = []
                c_tmp = []
                for index_obj in rule_obj.indexes:
                    tmp = []
                    h_i,c_i,sc_i = index_obj.word_order.split(' --> ')
                    h_i,c_i = int(h_i),int(c_i)
                    sc_i = map(int,sc_i.split(','))
                    if h_i > c_i:
                        tmp.append('%s:<-%s-%s-%s'%(role,'a',h,'R'))
                    else:
                        tmp.append('%s:<-%s-%s-%s'%(role,'a',h,'L'))

                    for i,x in enumerate(sc_i):
                        pos,role = sc[i],'c'
                        if '@' in sc[i]:
                            pos,role = sc[i].split('@')
                        if x < h_i:
                            tmp.append('%s:>-%s-%s-%s'%(role,'c',pos,'L'))
                        else:
                            tmp.append('%s:>-%s-%s-%s'%(role,'c',pos,'R'))

                    if tmp not in c_tmp:
                        c_tmp.append(tmp)
                        mix_r.append((tmp,index_obj.id))

                for m_r,id in mix_r:
                    etree = TETree('3',id)
                    all_id.append(id)
                    for l in m_r:
                        etree.set_waiting_nodes([l])
                        if '3' not in self.children:
                            self.children['3'] = {l:[etree]}
                        elif '3' in self.children and l not in self.children['3']:
                            self.children['3'][l] = [etree]
                        elif '3' in self.children and l in self.children['3'] and etree not in self.children['3'][l]:
                            self.children['3'][l].append(etree)
        return all_id
    def process(self,mtable,itable,relax=False,size=3):
        all_id = []
        my_strip = lambda x:x.strip('[').strip(']')

        def get_freq(rule,type,itable):
            freq = 0
            for idx in itable['%d:%s'%(type,rule[0])]:
                freq += len(idx[3])
            return freq
        
        # process Type-I tree
        rules = []
        for r in mtable.get('1:'+self.root,[]):
            rules.append((get_freq(r,1,itable),r))
        rules.sort()
        rules.reverse()

        if relax:
            rules = rules[:size]
            
        for freq,r in rules:
            h,c = r[0].split(' --> ')
            c = map(my_strip,c.split(','))
            h = my_strip(h)
            mix_r = []
            c_tmp = []
            for idx in itable['1:'+r[0]]:
                tmp = []
                h_i,c_i = idx[0].split(' --> ')
                h_i = int(h_i)
                c_i = map(int,c_i.split(','))
                for i,x in enumerate(c_i):
                    pos,role = c[i],'c'
                    if '@' in c[i]:
                        pos,role = c[i].split('@')
                    if x < h_i:
                        tmp.append('%s:>-%s-%s-%s'%(role,'c',pos,'L'))
                    else:
                        tmp.append('%s:>-%s-%s-%s'%(role,'c',pos,'R'))
                if tmp not in c_tmp:
                    c_tmp.append(tmp)
                    mix_r.append((len(idx[3]),tmp,idx[2]))

            for freq,m_r,id in mix_r:
                etree = TETree('1',id)
                all_id.append(id)
                for l in m_r:
                    etree.set_waiting_nodes([l])
                    if '1' not in self.children:
                        self.children['1'] = {l:[etree]}
                    elif '1' in self.children and l not in self.children['1']:
                        self.children['1'][l] = [etree]
                    elif '1' in self.children and l in self.children['1'] and etree not in self.children['1'][l]:
                        self.children['1'][l].append(etree)

        # process Type-II
        rules = []
        for r in mtable.get('2:'+self.root,[]):
            rules.append((get_freq(r,2,itable),r))
        rules.sort()
        rules.reverse()
            
        if relax:
            rules = rules[:size]
            
        for freq,r in rules[:size]:
            tp = r[0].split(' --> ')
            # Type-II
            if len(tp) == 2:
                h,c = map(my_strip,tp)
                pos,role = c,'a'
                if '@' in c:
                    pos,role = c.split('@')
                mix_r = []
                c_tmp = []
                for idx in itable['2:'+r[0]]:
                    h_i,c_i = map(int,idx[0].split(' --> '))
                    if h_i > c_i:
                        k = '%s:<-%s-%s-%s'%(role,'a',h,'R')
                        if k not in c_tmp:
                            c_tmp.append(k)
                            mix_r.append((len(idx[3]),k,idx[2]))
                    else:
                        k = '%s:<-%s-%s-%s'%(role,'a',h,'L')
                        if k not in c_tmp:
                            c_tmp.append(k)
                            mix_r.append((len(idx[3]),k,idx[2]))

                for freq,m_r,id in mix_r:
                    etree = TETree('2',id)
                    all_id.append(id)
                    etree.set_waiting_nodes([m_r])
                    if '2' not in self.children:
                        self.children['2'] = {m_r:[etree]}
                    elif '2' in self.children and m_r not in self.children['2']:
                        self.children['2'][m_r] = [etree]
                    elif '2' in self.children and m_r in self.children['2'] and etree not in self.children['2'][m_r]:
                        self.children['2'][m_r].append(etree)

        # process Type-III
        rules = []
        for r in mtable.get('3:'+self.root,[]):
            rules.append((get_freq(r,3,itable),r))
        rules.sort()
        rules.reverse()
            
        if relax:
            rules = rules[:size]
            
        for freq,r in rules[:size]:
            tp = r[0].split(' --> ')
            # Type-III
            if len(tp) == 3:
                h,c,sc = tp
                h,c = my_strip(h),my_strip(c)
                pos,role = c,'a'
                if '@' in c:
                    pos,role = c.split('@')
                sc = map(my_strip,sc.split(','))
                mix_r = []
                c_tmp = []
                for idx in itable['3:'+r[0]]:
                    tmp = []
                    h_i,c_i,sc_i = idx[0].split(' --> ')
                    h_i,c_i = int(h_i),int(c_i)
                    sc_i = map(int,sc_i.split(','))
                    if h_i > c_i:
                        tmp.append('%s:<-%s-%s-%s'%(role,'a',h,'R'))
                    else:
                        tmp.append('%s:<-%s-%s-%s'%(role,'a',h,'L'))

                    for i,x in enumerate(sc_i):
                        pos,role = sc[i],'c'
                        if '@' in sc[i]:
                            pos,role = sc[i].split('@')
                        if x < h_i:
                            tmp.append('%s:>-%s-%s-%s'%(role,'c',pos,'L'))
                        else:
                            tmp.append('%s:>-%s-%s-%s'%(role,'c',pos,'R'))

                if tmp not in c_tmp:
                    c_tmp.append(tmp)
                    mix_r.append((len(idx[3]),tmp,idx[2]))

                for freq,m_r,id in mix_r:
                    etree = TETree('3',id)
                    all_id.append(id)
                    for l in m_r:
                        etree.set_waiting_nodes([l])
                        if '3' not in self.children:
                            self.children['3'] = {l:[etree]}
                        elif '3' in self.children and l not in self.children['3']:
                            self.children['3'][l] = [etree]
                        elif '3' in self.children and l in self.children['3'] and etree not in self.children['3'][l]:
                            self.children['3'][l].append(etree)
        return all_id

def load_rules_from_text(rule_file):
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
                rule,prob,id = map(str.strip,line.split(':'))
                id = int(id[:id.find('#')].strip().split('=')[1])
            if flag == 'm':
                if key not in mtable:
                    mtable[key] = [(rule,float(prob))]
                else:
                    mtable[key].append((rule,float(prob)))
            elif flag == 'i':
                if key not in itable:
                    itable[key] = [(rule,float(prob),id)]
                else:
                    itable[key].append((rule,float(prob),id))
    return mtable,itable

def main():
    #mtable,itable = load_rules_from_text('data/train-all-22-04-2551.dig')
    trie = TrieETrees('และ/conj')
    #id = trie.process(mtable,itable)
    id = trie.process_db()
    print trie
    #id.sort()
    #print id

if __name__ == '__main__':
    main()
