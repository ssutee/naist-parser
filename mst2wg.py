#!/usr/bin/python

# a script for changing the MST format to the format which is easier to evaluate with the output from the lattice


import sys

lines = sys.__stdin__.readlines()

def get_wg(W,P,H):
    tmp_W = []
    ci = 0
    for i in range(len(W)):
        l = len(W[i].decode('utf8').encode('cp874'))
        w = '%s:%d:%d'%(W[i],ci,ci+l)
        tmp_W.append(w)
        ci += l
    W = tmp_W

    pairs = []
    for i in range(len(W)):
        h = H[i]
        if h != 0:
            s = '%s %s %s %s %s'%(W[h-1],P[h-1],'<--',W[i],P[i])
        else:
            s = '%s %s %s %s %s'%('ROOT','ROOT','<--',W[i],P[i])
        pairs.append(s)
    return '(+)'.join(pairs)
    

tmp = []
for line in lines:
    if line.strip() != '':
        tmp.append(line)
    else:
        for i in range(len(tmp)):
            if i%4 == 3:
                W = tmp[i-3].split()
                P = tmp[i-2].split()
                H = map(int,tmp[i].split())
                print get_wg(W,P,H)
        print ''
        tmp = []
