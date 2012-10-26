# Adapter for p'Ko dependency input/output.
import simplejson

def parse_input(input_str):
    """ Returns list of tuple: (surface string, JSON tree).
    """
    input_lines = input_str.strip().split("\n")
    i = 0
    json_trees = []
    while i < len(input_lines):
        surface = input_lines[i].strip().split("\t")
        pos = input_lines[i + 1].strip().split("\t")
        attr = input_lines[i + 2].strip().split("\t")
        dep = input_lines[i + 3].strip().split("\t")
        i += 5
        # print "surface: ", surface
        # print "pos: ", pos
        # print "dep: ", dep
        if len(surface) > 0:
            json_tree = create_json_tree(surface, pos, dep, attr)
            json_trees.append(("".join(surface), json_tree))
            # print "json_tree: ", json_tree
    return json_trees

def create_json_tree(surface, pos, dep, attr):
    """Returns JSON representation of given strings of surface, pos, dep
    Format:
    surface: "John	hit	the	ball"
    pos: "N	V	D	N"
    attr: "subj root    det dobj"
    dep: "2	0	4	2"
    0 indicates the root (head) of dependency tree, 1,... indicates index of the parent of current node (1st word is indexed 1.)
    """
    offsets = create_offset_list(surface)  # list of tuple (offset, length)
    
    # Creates node list
    nodes = []
    for i, s in enumerate(surface):
        new_node = {"stree": [offsets[i]], "pos": str(pos[i]), "type": "dependency", "dep_attr": str(attr[i])}
        nodes.append(new_node)
    
    # Create list of tuple: (dependency number, node)
    node_list = zip([int(d) for d in dep], nodes)
    node_list.sort()
    root = None;
    for (dep_no, node) in node_list:
        if dep_no == 0: # For head (root) node
            root = node
            continue
        
        parent = nodes[dep_no- 1]
        parent.setdefault("children", []).append(node)
    
    json_tree = repr([root])#simplejson.dumps(root)
    return json_tree

def create_offset_list(surface):
    """ Returns list of tuple (offset, length) of each word in surface form.
    """
    offset_list = []
    offset = 0
    for word in surface:
        length = len(word)
        offset_list.append([offset, length])
        offset += length
    return offset_list
    

def json_to_output(surface, json):
    root = simplejson.loads(json)
    return root_to_output(surface, root)
    
def root_to_output(surface, root):
    """ Returns output of given surface and tree(dictionary format) in following format.
    Format:
    John	hit	the	ball
    N	V	D	N
    2	0	4	2
    C	-	A	S
    Line 3: The dependency number:
            0 indicates the root (head) of dependency tree, 
            1,... indicates index of the parent of current node (1st word is indexed 1.)
    Line 4: C = Complement
            A = Adjunct
            S = Necessary adjunct
    """
    # Create lookup dictionary for dependency number
    queue = [root]
    dep_dict = {}
    node_list = []
    root["node_id"] = 0 # Dummy ID for easy lookup
    node_id_counter = 1
    while len(queue) != 0:
        node = queue.pop(0)
        
        # Create parental dictionary
        if len(node.setdefault("children", [])) > 0:
            for child in node["children"]:
                child["node_id"] = node_id_counter
                dep_dict[node_id_counter] = node
                node_id_counter += 1
            queue.extend(node["children"])
        node_list.append((node["stree"][0], node))
        
    node_list.sort()
    node_order_lookup = dict([(node_tuple[1]["node_id"], i) 
                             for i, node_tuple in enumerate(node_list)]
                            )
    
    # Create ordered list of surface, pos, dependency number, attribute.
    surface_list = []
    pos_list = []
    dep_list = []
    attr_list = []
    for i, (_, node) in enumerate(node_list):
        begin = int(node["stree"][0][0])
        end = int(node["stree"][0][0] + node["stree"][0][1])
        surface_list.append(surface[begin : end])
        pos_list.append(node.setdefault("pos", ""))
        attr_list.append(node.setdefault("dep_attr", "-"))
        
        parent = dep_dict.setdefault(node["node_id"], None)
        if parent is None:
            dep = 0
        else:
            dep = node_order_lookup[parent["node_id"]] + 1
        dep_list.append(str(dep))
    
    # print "surface_list: ", surface_list
    # print "pos_list: ", pos_list
    # print "dep_list: ", dep_list
    # print "attr_list: ", attr_list
    
    output = OUTPUT_FORMAT % dict(surface="\t".join(surface_list),
                                  pos="\t".join(pos_list),
                                  dep="\t".join(dep_list),
                                  attr="\t".join(attr_list),
                                  )
                                  
    return output
    
def test():
    assert(parse_input(TEST_INPUT) == TEST_PARSED)
    assert (json_to_output(TEST_SURFACE, TEST_JSON) == TEST_OUTPUT)

TEST_INPUT = \
u"""เว็บบราวเซอร์	แบบ	หลาย	ภาษา
npn	ncn	adj	ncn
0	1	4	1"""

TEST_SURFACE = u"เว็บบราวเซอร์แบบหลายภาษา"

TEST_JSON = u"""{'pos': 'npn', 'stree': [[0, 13]], 'children': [{'pos': 'ncn', 'stree': [[13, 3]]}, {'pos': 'ncn', 'stree': [[20, 4]], 'children': [{'pos': 'adj', 'stree': [[16, 4]]}]}]}"""

TEST_PARSED = \
[(TEST_SURFACE, TEST_JSON)]

TEST_OUTPUT = TEST_INPUT + "\n\t\t\t"

OUTPUT_FORMAT =\
"""%(surface)s
%(pos)s
%(attr)s
%(dep)s"""

if __name__ == "__main__":
    test()
