#!/usr/bin/python2.5

import sys,os,re
#sstc_parser_path = os.path.join(os.path.dirname(sys.argv[0]), os.pardir, 'sstc_parser')
#sys.path.insert(0, os.path.abspath(sstc_parser_path))

#import sstc_parser
import xml.etree.ElementTree as ET

from naist_parser.maxent_utils import generate_features,create_between_pos_table,extract_features
from naist_parser.common_utils import decode_punc,encode_number,get_simplified_pos

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

def get_pos_features(ptable,word):
    pos = []
    if word in ptable:
        pos = ptable[word]
    return ' '.join(map(lambda x: str(x in pos), all_pos))

def get_simplified_pos_features(ptable,word):
    pos = []
    if word in ptable:
        pos = ptable[word]
    sim_pos = map(get_simplified_pos,pos)
    return ' '.join(map(lambda x: str(x in sim_pos), all_simplified_pos))

def is_content_word(pos):
    if pos in Noun+Verb+Adjective+Adverb: return 'True'
    return 'False'

def extract_training_features(e,child,itable):
    if e == 'U-HEAD':
        pword,ppos,pspos = 'U-HEAD','U-HEAD','U-HEAD'
        psnode = -1
        piscon = False
    else:
        pword = e.get('word').replace(' ','_')
        ppos = e.get('pos')
        psnode = map(int,e.get('snode').split('_'))
        pspos = get_simplified_pos(ppos)
        piscon = is_content_word(ppos)

    cword = child.get('word').replace(' ','_')
    cpos = child.get('pos')
    csnode = map(int,child.get('snode').split('_'))
    cspos = get_simplified_pos(cpos)
    ciscon = is_content_word(cpos)

    skip = str(abs(psnode[1]-csnode[0]))

    loc = 'R'
    if psnode[0] > csnode[0]:
        loc = 'L'

    if psnode > -1:
        i = itable.index([psnode[0],psnode[1],pword,ppos])
        if i == 0: # starting node
            ppword,pppos = '-S-','-S-'
        elif i == len(itable)-1: # ending node
            npword,nppos = '-E-','-E-'
        if i != 0:
            x,x,ppword,pppos = itable[i-1]
        if i != len(itable)-1:
            x,x,npword,nppos = itable[i+1]
    else:
        ppword,pppos,npword,nppos = 'U-HEAD','U-HEAD','U-HEAD','U-HEAD'

    j = itable.index([csnode[0],csnode[1],cword,cpos])
    if j == 0: # starting node
        pcword,pcpos = '-S-','-S-'
    elif j == len(itable)-1: # ending node
        ncword,ncpos = '-E-','-E-'
    if j != 0:
        x,x,pcword,pcpos = itable[j-1]
    if j != len(itable)-1:
        x,x,ncword,ncpos = itable[j+1]

    features = generate_features(pword,ppos,cword,cpos,ppword,pppos,npword,nppos,pcword,pcpos,ncword,ncpos,loc,skip)
    
    return features

def filter_blank(etree):
    if etree.getchildren() == []:
        if etree.get('word') == None:
            return ET.Element('node')
        if etree.get('word') == '_':
            return None
        word = etree.get('word')
        pos = etree.get('pos')
        snode = etree.get('snode')
        stree = etree.get('stree')
        node = ET.Element('node')
        node.set('word',word)
        node.set('pos',pos)
        node.set('snode',snode)
        node.set('stree',stree)
        return node
    node = ET.Element('node')
    word = etree.get('word')
    pos = etree.get('pos')
    snode = etree.get('snode')
    stree = etree.get('stree')
    node = ET.Element('node')
    node.set('word',word)
    node.set('pos',pos)
    node.set('snode',snode)
    node.set('stree',stree)
    for child in etree.getchildren():
        subnode = filter_blank(child)
        if subnode != None:
            node.append(subnode)
    return node
        

def delete_blank(etree,text):
    # find position of blank word
    mark = []
    for i,word in enumerate(text.split()):
        if word == '_':
            mark.append(i)  

    # recompute snode in etree
    blank_node = []
    for node in etree.getiterator():
        if node.get('snode') != None:
            x,y = map(int,node.get('snode').split('_'))
            for m in mark:
                if x > m:
                    x-=1
            node.set('snode','%d_%d'%(x,x+1))
        if node.get('word') == '_':
            blank_node.append(node)

    # remove blank word from etree
    etree = filter_blank(etree.getroot())
    etree = ET.ElementTree(etree)
            

    # recompute stree
    for node in etree.getiterator():
        if node.get('stree') == None: continue
        tmp = []
        for child in node.getiterator():
            x,y = map(int,child.get('snode').split('_'))
            tmp.append(x)
            tmp.append(y)
        node.set('stree','%d_%d'%(min(tmp),max(tmp)))
    return etree

def recompute_itable(itable,text):
    # find position of blank word
    mark = []
    for i,word in enumerate(text.split()):
        if word == '_':
            mark.append(i)  

    # recompute snode in itable
    tmp = []
    for i,(x,y,w,p) in enumerate(itable):
        for m in mark:
            if x > m:
                x-=1
        itable[i][0] = x    
        itable[i][1] = x+1
        if w == '_':
            tmp.append(itable[i])
    # remove blank word from itable
    for t in tmp:
        itable.remove(t)
    return itable
            
def print_tree(tree,s):
    if tree.getchildren() == []:
        return '%s/%s'%(tree.get('word'),tree.get('pos'))
    s = '%s/%s'%(tree.get('word'),tree.get('pos'))
    s += '( '
    for child in tree.getchildren():
        s += print_tree(child,s) + ','
    s = s.strip(',') + ' )'
    return s


#def gen_events(sstc,text):
#   parser = sstc_parser.SSTCParser()
#   etree = parser.parse(sstc,text)
#
#   etree = delete_blank(etree,text)
#   parser.itable = recompute_itable(parser.itable,text)    

#   text = text.replace('_','')

#   positive = []
#   for e in etree.getiterator():
#       if e.get('word') == None: continue
#       children = e.getchildren()
#       if children != []:
#           for child in children:
#               positive.append(extract_training_features(e,child,parser.itable))

#   negative = []
#   for e1 in etree.getiterator():
#       for e2 in etree.getiterator():
#           if e1.get('word') == None or e2.get('word') == None: continue
#           if e1 != e2:
#               f = extract_training_features(e1,e2,parser.itable)
#               if f not in positive:
#                   negative.append(f)
#
#   pe = '\n'.join(map(lambda x:'Yes '+x,positive)).strip()
#   ne = '\n'.join(map(lambda x:'No '+x,negative)).strip()
#
#   return pe,ne


'''
def gen_events(sstc,text):
    parser = sstc_parser.SSTCParser()
    etree = parser.parse(sstc,text)
    positive = []
    negative = []
    for e in etree.getiterator():
        if e.get('word') == None: continue
        children = e.getchildren()
        if children != []:
            for child in children:
                positive.append(extract_training_features(e,child,parser.itable))
                negative.append(extract_training_features(child,e,parser.itable))

    pe = '\n'.join(map(lambda x:'Yes '+x,positive)).strip()
    ne = '\n'.join(map(lambda x:'No '+x,negative)).strip()

    return pe,ne
'''

def main_old():
    lines = sys.__stdin__.readlines()
    train_file = open('train.data','w')
    ne_test_file = open('ne_test.data','w')
    pe_test_file = open('pe_test.data','w')
    all_test_file = open('all_test.data','w')
    total_file = open('total.data','w')

    i = 0
    for line in lines:
        if line.find('St:') == 0:
            sstc = line[3:].strip()
        if line.find('Ss:') == 0:
#           try:
            text = line[3:].strip()
            pe,ne = gen_events(sstc,text)
            i += 1
            total_file.write(pe+'\n')
            total_file.write(ne+'\n')
            if i%10 == 0:
                pe_test_file.write(pe+'\n')
                ne_test_file.write(ne+'\n')
                all_test_file.write(pe+'\n'+ne+'\n')
            else:
                train_file.write(pe+'\n')
                train_file.write(ne+'\n')
#           except AttributeError,e:
#               print e
#               pass

    train_file.close()
    pe_test_file.close()
    ne_test_file.close()
    all_test_file.close()
    total_file.close()

def main():
    lines = sys.__stdin__.readlines()
    tmp = []

    for line in lines:
        if line.strip() != '':
            tmp.append(line.strip())
        else:
            W = ['<root>'] + map(encode_number,map(str.strip,tmp[0].split('\t')))
            T = ['<root-POS>'] + map(str.strip,tmp[1].split('\t'))
            H = [-1] + map(str.strip,tmp[-1].split('\t'))

            if len(W) < 2:
                continue

            nW = []
            for i in range(len(W)):
                if T[i] == 'npn':
                    nW.append('<npn>')
                else:
                    nW.append(W[i])
            W = nW

            units = [(W[i].replace(' ','_'),T[i],H[i]) for i in range(len(W))]
            pairs = [(int(h),i) for i,h in enumerate(H)]

            b_table = create_between_pos_table(T)

            for i in range(len(W)):
                for j in range(i+1,len(W),1):
                    for di in ['L','R']:
                        ans = 'No'
                        if (di == 'L' and (j,i) in pairs) or (di == 'R' and (i,j) in pairs):
                            ans = 'Yes'
                        print ans,extract_features(i,j,di,units,b_table)
            tmp = []

if __name__ == '__main__':
    main()
