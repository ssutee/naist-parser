#!/usr/bin/python2.5

from maxent_utils import create_between_pos_table,gen_features
from common_utils import get_simplified_pos,mst2etree
import sys

def gen_label_feature(root,child,l_sibling,r_sibling,context,s_len,b_table):
    # edges
    h_word,h_pos = root.get('word'),root.get('pos')
    c_word,c_pos = child.get('word'),child.get('pos')
    h_spos,c_spos = get_simplified_pos(h_pos),get_simplified_pos(c_pos)
    h_role = root.get('role')
    c_args = child.get('args')

    h_id = map(int,root.get('snode').split('_'))[0]
    c_id = map(int,child.get('snode').split('_'))[0]

    is_first,is_last = 'No','No'
    if c_id == 0:
        is_first = 'Yes'
    if c_id == s_len:
        is_last = 'Yes'
    di = 'R'
    if h_id > c_id:
        di = 'L'

    # children of child
    cc_poses = []
    if len(child.getchildren()) != []:
        for cc in child.getchildren():
            cc_poses.append(cc.get('pos'))
    has_prel = 'No'
    if 'prel' in cc_poses:
        has_prel = 'Yes'

    # siblings
    r_word,r_pos,r_spos = 'None','None','None'
    l_word,l_pos,l_spos = 'None','None','None'
    if r_sibling != None:
        r_word,r_pos = r_sibling.get('word'),r_sibling.get('pos')
    if l_sibling != None:
        l_word,l_pos = l_sibling.get('word'),l_sibling.get('pos')

    # context
    context_pos = []
    if h_id < c_id:
        key = '%s-%s'%(h_id+1,c_id+1)
        if key in b_table:
            context_pos = b_table[key]
        tmp = range(h_id+1,c_id)
    else:
        key = '%s-%s'%(c_id+1,h_id+1)
        if key in b_table:
            context_pos = b_table[key]
        tmp = range(c_id+1,h_id)
    context_id = map(lambda x:x[0],context)
    between_same_head = 'Yes'
    for x in tmp:
        if x not in context_id:
            between_same_head = 'No'
            break

    # non-local
    mods_of_child = len(child.getchildren())

    first_sibling_id = context[0][0]
    last_sibling_id = context[-1][0]

    is_right_most,is_left_most = 'No','No'
    is_first_right,is_first_left = 'No','No'

    l_tmp,r_tmp = [],[]
    if h_id > first_sibling_id and h_id < last_sibling_id:
        for id in context_id:
            if id < h_id:
                l_tmp.append(id)
            else:
                r_tmp.append(id)
    elif h_id > first_sibling_id and h_id > last_sibling_id:
        l_tmp = context_id
        r_tmp = [None]
    elif h_id < first_sibling_id and h_id < last_sibling_id:
        r_tmp = context_id
        l_tmp = [None]

    if c_id == l_tmp[0]:
        is_left_most = 'Yes'
    if c_id == r_tmp[-1]:
        is_right_most = 'Yes'
    if c_id == l_tmp[-1]:
        is_first_left = 'Yes'
    if c_id == r_tmp[0]:
        is_first_right = 'Yes'

    if c_args != 'unknown':
        c_args_features = [h_pos,c_pos,h_role,c_args],\
                          [h_spos,c_spos,h_role,c_args],\
                          [h_pos,c_pos,di,h_role,c_args],\
                          [h_spos,c_spos,di,h_role,c_args],\
                          [h_word,h_pos,c_word,c_pos,is_first,is_last,di,h_role,c_args],\
                          [h_word,h_spos,c_word,c_spos,is_first,is_last,di,h_role,c_args],\
                          [h_pos,c_pos,is_first,is_last,di,h_role,c_args],\
                          [h_spos,c_spos,is_first,is_last,di,h_role,c_args],\
                          [h_pos,c_pos,is_first,is_last,h_role,c_args],\
                          [h_spos,c_spos,is_first,is_last,h_role,c_args]
    else:
        c_args_features = None,None,None,None,None,None,None,None,None,None,

    return gen_features( 
                    [h_word,h_pos,c_word,c_pos,is_first,is_last,di], # edge features
                    [h_word,h_spos,c_word,c_spos,is_first,is_last,di], 
                    [h_pos,c_pos,is_first,is_last,di], 
                    [h_spos,c_spos,is_first,is_last,di], 
                    [h_pos,c_pos,is_first,is_last],
                    [h_spos,c_spos,is_first,is_last],
                    [h_pos,c_pos,di],
                    [h_spos,c_spos,di],
                    [h_pos,c_pos],
                    [h_spos,c_spos],

                    [h_pos,c_pos,h_role],
                    [h_spos,c_spos,h_role],
                    [h_pos,c_pos,di,h_role],
                    [h_spos,c_spos,di,h_role],
                    [h_word,h_pos,c_word,c_pos,is_first,is_last,di,h_role], 
                    [h_word,h_spos,c_word,c_spos,is_first,is_last,di,h_role], 
                    [h_pos,c_pos,is_first,is_last,di,h_role], 
                    [h_spos,c_spos,is_first,is_last,di,h_role], 
                    [h_pos,c_pos,is_first,is_last,h_role],
                    [h_spos,c_spos,is_first,is_last,h_role],

                    c_args_features,

                    [c_pos,has_prel],
                    [c_spos,has_prel],
                    [c_pos,di,has_prel],
                    [c_spos,di,has_prel],

                    [l_word,l_pos,r_word,r_pos], # sibiling features
                    [l_word,l_spos,r_word,r_spos], 
                    [l_pos,r_pos], 
                    [l_spos,r_spos], 

                    between_same_head, # context features

                    [str(mods_of_child),is_right_most,is_left_most,is_first_right,is_first_left], # non-local features
                    [str(mods_of_child)],
                    [is_right_most,is_left_most],
                    [is_first_right,is_first_left], 
                    [str(mods_of_child),is_right_most,is_left_most],
                    [str(mods_of_child),is_first_right,is_first_left], 
                    [is_right_most,is_left_most,is_first_right,is_first_left],
               )

def extract_label_features(root,s_len,b_table):
    children = root.getchildren()

    tmp = []
    for child in children: 
        snode = map(int,child.get('snode').split('_'))
        tmp.append((snode[0],child))
    tmp.sort() #sorting child nodes

    for i,(snode,child) in enumerate(tmp):
        if i > 0 and i < len(tmp)-1:
            l_sibling,r_sibling = tmp[i-1][1],tmp[i+1][1]
        elif i < len(tmp)-1:
            l_sibling,r_sibling = None,tmp[i+1][1]
        elif i > 0:
            l_sibling,r_sibling = tmp[i-1][1],None
        else:
            l_sibling,r_sibling = None,None
        if root.get('word') != None:
            feature = gen_label_feature(root,child,l_sibling,r_sibling,tmp,s_len,b_table)
            print child.get('role'),feature
        extract_label_features(child,s_len,b_table)

def compute_label(root,s_len,b_table,results,model):
    children = root.getchildren()

    tmp = []
    for child in children: 
        snode = map(int,child.get('snode').split('_'))
        tmp.append((snode[0],child))
    tmp.sort() #sorting child nodes

    for i,(snode,child) in enumerate(tmp):
        if i > 0 and i < len(tmp)-1:
            l_sibling,r_sibling = tmp[i-1][1],tmp[i+1][1]
        elif i < len(tmp)-1:
            l_sibling,r_sibling = None,tmp[i+1][1]
        elif i > 0:
            l_sibling,r_sibling = tmp[i-1][1],None
        else:
            l_sibling,r_sibling = None,None
        if root.get('word') != None:
            feature = gen_label_feature(root,child,l_sibling,r_sibling,tmp,s_len,b_table)
            evals = model.eval_all(feature.split())
            roles = child.get('role').split('/')
            #print roles,evals # for debugging
            #print ''
            if child.get('role').strip() == '-':
                child.set('role',evals[0][0])
                #child.set('role','-')
            elif len(roles) > 1:
                for ev in evals:
                    if ev[0] in roles:
                        child.set('role',ev[0])
                        break
            id = int(child.get('snode').split('_')[0])
            results.append((id,child.get('role')))
        compute_label(child,s_len,b_table,results,model)

