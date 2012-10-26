# this file contains neccessary modules for Maxent 
import sys
from common_utils import *

def create_between_pos_table(tags):
    table = {}
    for i in range(len(tags)-2):
        table['%d-%d'%(i,i+2)] = [tags[i+1]]
    for l in range(3,len(tags)+1,1):
        for i in range(len(tags)):
            if i+l >= len(tags): break
            table['%d-%d'%(i,i+l)] = table['%d-%d'%(i,i+l-1)] + [tags[i+l-1]]
    return table

def gen_features(*args,**kw):
    tmp = []
    i = 1
    j = 0
    for x in args:
        if isinstance(x,tuple):
            for y in x:
                if isinstance(y,list):
                    tmp.append('%d-%s'%(i,'/'.join(y)))
                    i+=1
                elif y == None:
                    i+=1
                    j+=1
                else:
                    tmp.append('%d-%s'%(i,y))
                    i+=1
        elif isinstance(x,list):
            tmp.append('%d-%s'%(i,'/'.join(x)))
            i+=1
        elif x == None:
            i+=1
            j+=1
        else:
            tmp.append('%d-%s'%(i,x))
            i+=1

    pat = '%s '*(i-1-j)

    return pat.strip() % tuple(tmp) 

def extract_features(i,j,loc,units,b_table,start=True,end=True): 
    wi,ti = decode_punc(units[i][0]),units[i][1]
    si = get_simplified_pos(ti)

    wj,tj = decode_punc(units[j][0]),units[j][1]
    sj = get_simplified_pos(tj)

    skip = abs(i-j)-1
    if skip >= 5: skip = 5
    if skip >= 10: skip = 10
    if skip >= 15: skip = 15
    skip = str(skip)

    if i == 0 and start: 
        tpi,spi = '-S-','-S-'
    elif i == 0 and not start:
        tpi,spi = None,None
    else:
        tpi = units[i-1][1]
        spi = get_simplified_pos(tpi)

    if j == len(units)-1 and end: 
        tnj,snj = '-E-','-E-'
    elif j == len(units)-1 and not end:
        tnj,snj = None,None
    else:
        tnj = units[j+1][1]
        snj = get_simplified_pos(tnj)

    if i != j-1:
        tni = units[i+1][1]
        sni = get_simplified_pos(tni)
        tpj = units[j-1][1]
        spj = get_simplified_pos(tpj)
    else:
        tni,sni = '-M-','-M-'
        tpj,spj = '-M-','-M-'

    bf = []
    if abs(i-j) > 1:
        bf = b_table['%d-%d'%(i,j)]
        bf = list(set(bf))
        bf.sort()

    features = generate_features(
        wi,ti,si,
        wj,tj,sj,
        tpi,spi,
        tni,sni,
        tpj,spj,
        tnj,snj,
        loc,skip,bf)
    
    return features

def mix(F1,F2):
    F = []
    for f1 in F1:
        for f2 in F2:
            if f1 == None or f2 == None:
                F.append(None)
            else:
                if type(f1) == str and type(f2) == str:
                    F.append([f1]+[f2])
                elif type(f1) == list and type(f2) == str:
                    F.append(f1+[f2])
                elif type(f1) == str and type(f2) == list:
                    F.append([f1]+f2)
                elif type(f1) == list and type(f2) == list:
                    F.append(f1+f2)
                else:
                    print 'error'
                    sys.exit(1)
    return tuple(F)

# input are parent, child, their neighbors, and position
#           'skip' and 'loc' is parent and child relative position
def generate_features(
        wi,ti,si,
        wj,tj,sj,
        tpi,spi,
        tni,sni,
        tpj,spj,
        tnj,snj,
        loc,skip,bf):

    bpos,bspos = None,None
    if bf != []:
        bf = list(set(bf))
        bpos = '+'.join(bf)
        sbf = map(get_simplified_pos,bf)
        sbf = list(set(sbf))
        bspos = '+'.join(sbf)

    if loc == 'R':
        wh,wc = wi,wj
        th,tc = ti,tj
        sh,sc = si,sj
    elif loc == 'L':
        wh,wc = wj,wi
        th,tc = tj,ti
        sh,sc = sj,si

    # Unigram features
    unigram = (
        wh,  # Wi
        wc,  # Wj
        th,   # Ti
        tc,   # Tj
        sh,  # Si
        sc,  # Sj
        [wh,th],   
        [wc,tc],   
        [wh,sh], 
        [wc,sc])

    # Bigram features
    bigram = (
        [wh,wc],   # Wi/Wj
        [th,tc],     # Ti/Tj
        [sh,sc],   # Si/Sj
        [th,wc,tc],   # Ti/Wj/Tj
        [wh,wc,tc],  # Wi/Wj/Tj
        [wh,th,tc],   # Wi/Ti/Tj
        [wh,th,wc],  # Wi/Ti/Wj
        [sh,wc,sc], # Si/Wj/Sj
        [wh,wc,sc], # Wi/Wj/Sj
        [wh,sh,sc], # Wi/Si/Sj
        [wh,sh,wc], # Wi/Si/Wj
        [wh,th,wc,tc],     # Wi/Ti/Wj/Tj
        [wh,sh,wc,sc])   # Wi/Si/Wj/Sj

    # Surround features
    # Tags
    sf1,sf2,sf3,sf4,sf5,sf6,sf7,sf8,sf9,sf10 = (
        [ti,tni,tpj,tj],      # Ti/Ti+1/Tj-1/Tj
        [tpi,ti,tpj,tj],      # Ti-1/Ti/Tj-1/Tj
        [ti,tni,tj,tnj],      # Ti/Ti+1/Tj/Tj+1
        [tpi,ti,tj,tnj],      # Ti-1/Ti/Tj/Tj+1
        [tpi,ti],            # Ti-1/Ti
        [ti,tni],            # Ti/Ti+1
        [tpi,ti,tni],   # Ti-1/Ti/Ti+1
        [tpj,tj],            # Tj-1/Tj
        [tj,tnj],            # Tj/Tj+1
        [tpj,tj,tnj])   # Tj-1/Tj/Tj+1
    if tni == None:
        sf1,sf3,sf6,sf7 = None,None,None,None
    if tpi == None:
        sf2,sf4,sf5,sf7 = None,None,None,None
    if tnj == None:
        sf3,sf4,sf9,sf10 = None,None,None,None
    if tpj == None:
        sf1,sf2,sf8,sf10 = None,None,None,None
    surround_t = (sf1,sf2,sf3,sf4,sf5,sf6,sf7,sf8,sf9,sf10)

    # Simplified tags
    ssf1,ssf2,ssf3,ssf4,ssf5,ssf6,ssf7,ssf8,ssf9,ssf10 = (
        [si,sni,spj,sj],      # Ti/Ti+1/Tj-1/Tj
        [spi,si,spj,sj],      # Ti-1/Ti/Tj-1/Tj
        [si,sni,sj,snj],      # Ti/Ti+1/Tj/Tj+1
        [spi,si,sj,snj],      # Ti-1/Ti/Tj/Tj+1
        [spi,si],            # Ti-1/Ti
        [si,sni],            # Ti/Ti+1
        [spi,si,sni],   # Ti-1/Ti/Ti+1
        [spj,sj],            # Tj-1/Tj
        [sj,snj],            # Tj/Tj+1
        [spj,sj,snj])   # Tj-1/Tj/Tj+1
    if sni == None:
        ssf1,ssf3,ssf6,ssf7 = None,None,None,None
    if spi == None:
        ssf2,ssf4,ssf5,ssf7 = None,None,None,None
    if snj == None:
        ssf3,ssf4,ssf9,ssf10 = None,None,None,None
    if spj == None:
        ssf1,ssf2,ssf8,ssf10 = None,None,None,None
    surround_st = (ssf1,ssf2,ssf3,ssf4,ssf5,ssf6,ssf7,ssf8,ssf9,ssf10)

    # between POS features
    if bpos != None:
        bt_t = (
            [ti,bpos,tj], # Only POS
        )
    else:
        bt_t = (None,)

    # between S-POS features
    if bspos != None:
        bt_st = (
            [si,bspos,sj],
        )
    else:
        bt_st = (None,)

    features = gen_features(
        unigram,
        skip,
        loc,
        mix(unigram,(skip,)),
        mix(unigram,(loc,)),
        mix(unigram,([skip,loc],)),
        bigram,
        mix(bigram,(skip,)),
        mix(bigram,(loc,)),
        mix(bigram,([skip,loc],)),
        surround_t,
        mix(surround_t,(skip,)),
        mix(surround_t,(loc,)),
        mix(surround_t,([skip,loc],)),
        surround_st,
        mix(surround_st,(skip,)),
        mix(surround_st,(loc,)),
        mix(surround_st,([skip,loc],)),
        bt_t,
        mix(bt_t,(skip,)),
        mix(bt_t,(loc,)),
        mix(bt_t,(skip,loc,)),
        bt_st,
        mix(bt_st,(skip,)),
        mix(bt_st,(loc,)),
        mix(bt_st,(skip,loc,)),
        )
    return features
