#!/usr/bin/python

# a script for word graphs evaluation

import sys

def evaluate(gold_tokens,test_tokens):
    correct = 0
    complete,root_acc = False,False

    for t in test_tokens:
        if t in gold_tokens:
            correct += 1
        if t.find('ROOT ROOT') > -1 and t in gold_tokens:
            root_acc = True

    if correct == len(test_tokens):
        complete = True

    test_words = []
    for t in test_tokens:
        test_words += map(str.strip,t.split(' <-- '))
    test_words = list(set(test_words))

    gold_words = []
    for t in gold_tokens:
        gold_words += map(str.strip,t.split(' <-- '))
    gold_words = list(set(gold_words))

    c_word,g_word,t_word = 0,0,0
    for w in test_words:
        if w in gold_words:
            c_word += 1
        else:
            pass
    g_word += len(gold_words)-1
    t_word += len(test_words)-1
    c_word -= 1

    return correct,complete,root_acc,g_word,t_word,c_word

def k_evaluate(gold_file,test_file):
    f = lambda x: x.strip() != ''
    gold_lines = filter(f,open(gold_file).readlines())
    test_lines = []

    tmp = []
    lines = open(test_file).readlines()

    if lines[-1].strip() != '':
        lines.append('')

    for line in open(test_file).readlines():
        if line.strip() != '':
            tmp.append(line)
        else:
            test_lines.append(tmp)
            tmp = []

    if len(gold_lines) != len(test_lines):
        print 'two files mismatched'
        sys.exit(1)

    t_correct = 0
    t_test = 0
    t_gold = 0
    root_acc = 0
    c_word = 0
    g_word = 0
    t_word = 0
    complete_rate = 0
    for i in range(len(gold_lines)):
        gold_tokens = map(str.strip,gold_lines[i].split('(+)'))
        tmp = []
        for test_line in test_lines[i]:
            test_tokens = map(str.strip,test_line.split('(+)'))
            tmp.append(evaluate(gold_tokens,test_tokens))
        tmp.sort()
        tmp.reverse()

        correct,complete,root_ok,g_w,t_w,c_w = tmp[0]

        t_correct += correct
        t_test += len(test_tokens)
        t_gold += len(gold_tokens)
        if complete:
            complete_rate += 1
        if root_ok:
            root_acc += 1
        c_word += c_w
        g_word += g_w
        t_word += t_w

    t_precision = 1.0*t_correct/t_gold
    t_recall = 1.0*t_correct/t_test
    t_f = 2*t_precision*t_recall/(t_precision+t_recall)
    print 'correct tokens',t_correct
    print 'total tokens',t_gold
    print 'total','F',t_f,'P',t_precision,'R',t_recall
    print 'root acc',root_acc,root_acc*100.0/len(gold_lines)
    print 'complete rate',complete_rate,complete_rate*100.0/len(gold_lines)

    tR = 100.0*c_word/t_word
    tP = 100.0*c_word/g_word
    tF = (2*tR*tP)/(tR+tP)
    print c_word,g_word,t_word,'R',100.0*c_word/t_word,'P',100.0*c_word/g_word,'F',tF
            
def step_evaluate(gold_file,test_file):
    f = lambda x: x.strip() != ''
    gold_lines = filter(f,open(gold_file).readlines())
    test_lines = filter(f,open(test_file).readlines())

    if len(gold_lines) != len(test_lines):
        print 'two files mismatched'
        sys.exit(1)

    t_correct = [0,0,0,0]
    t_test = [0,0,0,0]
    t_gold = [0,0,0,0]
    root_acc = [0,0,0,0]
    complete_rate = [0,0,0,0]

    c_word = 0
    g_word = 0
    t_word = 0
    for i in range(len(gold_lines)):
        gold_tokens = map(str.strip,gold_lines[i].split('(+)'))
        test_tokens = map(str.strip,test_lines[i].split('(+)'))

        correct,complete,root_ok,g_w,t_w,c_w = evaluate(gold_tokens,test_tokens)

        if g_w <= 10:
            step = 0
        elif g_w > 10 and g_w <=20:
            step = 1
        elif g_w > 20:
            step = 2

        t_correct[step] += correct
        t_test[step] += len(test_tokens)
        t_gold[step] += len(gold_tokens)
        if complete:
            complete_rate[step] += 1
        if root_ok:
            root_acc[step] += 1


        c_word += c_w
        g_word += g_w
        t_word += t_w


    for step in range(3):
        t_precision = 1.0*t_correct[step]/t_gold[step]
        t_recall = 1.0*t_correct[step]/t_test[step]
        t_f = 2*t_precision*t_recall/(t_precision+t_recall)
        print step
        print 'correct tokens',t_correct[step]
        print 'total tokens',t_gold[step]
        print 'total','F',t_f,'P',t_precision,'R',t_recall
        print 'root acc',root_acc[step],root_acc[step]*100.0/len(gold_lines)
        print 'complete rate',complete_rate[step],complete_rate[step]*100.0/len(gold_lines)
        print ''

    tR = 100.0*c_word/t_word
    tP = 100.0*c_word/g_word
    tF = (2*tR*tP)/(tR+tP)
    print c_word,g_word,t_word,'R',100.0*c_word/t_word,'P',100.0*c_word/g_word,'F',tF

    
def single_evaluate(gold_file,test_file):
    f = lambda x: x.strip() != ''
    gold_lines = filter(f,open(gold_file).readlines())
    test_lines = filter(f,open(test_file).readlines())

    if len(gold_lines) != len(test_lines):
        print 'two files mismatched'
        sys.exit(1)
    

    t_correct = 0
    t_test = 0
    t_gold = 0
    root_acc = 0
    c_word = 0
    g_word = 0
    t_word = 0
    complete_rate = 0
    for i in range(len(gold_lines)):
        gold_tokens = map(str.strip,gold_lines[i].split('(+)'))
        test_tokens = map(str.strip,test_lines[i].split('(+)'))

        correct,complete,root_ok,g_w,t_w,c_w = evaluate(gold_tokens,test_tokens)

        t_correct += correct
        t_test += len(test_tokens)
        t_gold += len(gold_tokens)
        if complete:
            complete_rate += 1
            print i
        if root_ok:
            root_acc += 1
        c_word += c_w
        g_word += g_w
        t_word += t_w


    t_precision = 1.0*t_correct/t_gold
    t_recall = 1.0*t_correct/t_test
    t_f = 2*t_precision*t_recall/(t_precision+t_recall)
    print 'correct tokens',t_correct
    print 'total tokens',t_gold
    print 'total','F',t_f,'P',t_precision,'R',t_recall
    print 'root acc',root_acc,root_acc*100.0/len(gold_lines)
    print 'complete rate',complete_rate,complete_rate*100.0/len(gold_lines)

    tR = 100.0*c_word/t_word
    tP = 100.0*c_word/g_word
    tF = (2*tR*tP)/(tR+tP)
    print c_word,g_word,t_word,'R',100.0*c_word/t_word,'P',100.0*c_word/g_word,'F',tF

if len(sys.argv) == 3:
    gold_file = sys.argv[1]
    test_file = sys.argv[2]
    single_evaluate(gold_file,test_file)
elif len(sys.argv) == 4:
    gold_file = sys.argv[1]
    test_file = sys.argv[2]
    if sys.argv[3] == 'k':
        k_evaluate(gold_file,test_file)
    elif sys.argv[3] == 'step':
        step_evaluate(gold_file,test_file)

