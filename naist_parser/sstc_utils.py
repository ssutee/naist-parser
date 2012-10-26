import elementtree.ElementTree as ET

def compute_stree(etree):
	tmp = []
	for node in etree:
		snode = map(int,node.get('snode').split('_'))
		tmp += snode
	return '%d_%d' % (min(tmp),max(tmp))

def convert_mst_to_deps(W,T,R):
	deps = []
	for i,r in enumerate(R):
		if r == 0: continue
		hword,hpos,hsnode = W[r-1],T[r-1],'%s_%s'%(r-1,r)
		cword,cpos,csnode = W[i],T[i],'%s_%s'%(i,i+1)
		dep = (hword,hpos,hsnode),(cword,cpos,csnode)
		deps.append(dep)

	return deps

# deps = [((hword,hpos,hsnode),(cword,cpos,csnode)),...]
def generate_sstc(deps):
	sstc = ''
	set_deps = set(deps)
	dtree = deps2tree(deps)
	st = etree2stree(dtree)
	ss = generate_string(dtree)
	sstc += 'St:%s\n' % (st)
	sstc += 'Ss:%s\n' % (ss)
	sstc += 'Tt:\n'
	sstc += 'Ts:\n'
	sstc += '- SNODE CORRESPONDENCE -\n'
	sstc += '- STREE CORRESPONDENCE -\n'
	sstc += 'Status:0\n\n'
	return sstc

def generate_ssstc(s_deps,t_deps):
	sstc = ''

	s_dtree = deps2tree(s_deps)
	st = etree2stree(s_dtree)
	ss = generate_string(s_dtree)

	t_dtree = deps2tree(t_deps)
	tt = etree2stree(t_dtree)
	ts = generate_string(t_dtree)

	sstc += 'St:%s\n' % (st)
	sstc += 'Ss:%s\n' % (ss)
	sstc += 'Tt:%s\n' % (tt)
	sstc += 'Ts:%s\n' % (ts)
	sstc += '- SNODE CORRESPONDENCE -\n'
	sstc += '- STREE CORRESPONDENCE -\n'
	sstc += 'Status:0\n\n'
	return sstc

# recursive call for converting dependency tuple to ElementTree
def _deps2tree(root,snode_root,links,mtable): 
	if snode_root not in links:
		return
	for child in links[snode_root]:
		n = ET.SubElement(root,'node')
		n.set('word',mtable[child][0])	
		n.set('pos',mtable[child][1])
		n.set('snode',child)
		_deps2tree(n,child,links,mtable)
	return

# convert dependency tuple to ElementTree
def deps2tree(deps): 
	links = {}
	mtable = {}
	# generage mapping table
	for s,t in deps:
		if s[2] not in links:
			links[s[2]] = [t[2]]
		else:
			links[s[2]].append(t[2])
		if s[2] not in mtable:
			mtable[s[2]] = (s[0],s[1])
		if t[2] not in mtable:
			mtable[t[2]] = (t[0],t[1])

	# find root node
	root = ''
	for s1 in links:
		isroot = True
		for s2 in links:
			if s1 in links[s2]:
				isroot = False
				break
		if isroot: 
			root = s1
			break
	
	eroot = ET.Element('node')
	eroot.set('word', mtable[root][0])
	eroot.set('pos', mtable[root][1])
	eroot.set('snode',root)

	_deps2tree(eroot,root,links,mtable)

	return eroot

def _etree2stree(etree,text):
	if etree.getchildren() == []:
		text += '%s[%s]:%s/%s'%(etree.get('word'),etree.get('pos'),etree.get('snode'),etree.get('snode'))
		return text
	else:
		stree = compute_stree(etree)
		text += '%s[%s]:%s/%s'%(etree.get('word'),etree.get('pos'),etree.get('snode'),stree)
		text += '('
		for node in etree:
			text = _etree2stree(node,text) + ','
		text = text.strip(',') + ')'
	return text

def etree2stree(etree):
	text = ''
	return _etree2stree(etree,text)

def generate_string(etree):
	tmp = []
	for node in etree.getiterator():
		word = node.get('word')
		if word == '-COMMA-': word = ','
		elif word == '-LRB-': word = '('
		elif word == '-RRB-': word = ')'
		snode = map(int,node.get('snode').split('_'))
		tmp.append((snode,word))
	tmp.sort()
	return ' '.join([x[1] for x in tmp])
