#!/usr/bin/env python

from naist_parser.naist_parser import NAISTParser
import json, codecs
import os, os.path

from flask import Flask, request
app = Flask(__name__)

PARSER_PATH = '/home/sutee/naist-parser'

parser = NAISTParser(
    dig_file=os.path.join(PARSER_PATH,'naist_parser/data/deps.dig'),
    model_file=os.path.join(PARSER_PATH,'naist_parser/data/deps.model.txt'),
    label_model_file=os.path.join(PARSER_PATH,'naist_parser/data/deps.label.model.txt'))

def traverse(node, nodes=[], deps=[]):
    n = [(node['snode'][0]['s'], node['snode'][0]['e']), node['snode'][0]['text'], node['pos']]
    nodes.append(n)
    for child in node['children']:
        c = [(child['snode'][0]['s'], child['snode'][0]['e']), child['snode'][0]['text'], child['pos']]
        deps.append((n,c))
        traverse(child, nodes, deps)
    nodes.sort()
    return nodes, deps

def parse_sstc(json_input):
    json_obj = json.loads(json_input)
    root = json_obj['sstc']['tree'][0]
    nodes, deps = traverse(root, [])
    return ' '.join(map(lambda x: x[1]+'/'+x[2], nodes)), map(lambda x:x[0], nodes), map(lambda x:(x[0][0],x[1][0]), deps)

def parse_diff_nodes(json_input):
    json_obj = json.loads(json_input)
    diff_nodes = map(lambda x:tuple(map(int, x['id'].split('-'))) ,json_obj['differences'])
    diff_nodes.sort()
    return diff_nodes

def process_json_input(json_input):
    text, nodes, deps = parse_sstc(json_input)
    diff_nodes = parse_diff_nodes(json_input)
    fixed_deps = filter(lambda x: x[0] in diff_nodes and x[1] in diff_nodes, deps)
    fixed_deps = map(lambda x: (nodes.index(x[0]), nodes.index(x[1])), fixed_deps)
    return text, fixed_deps

@app.route('/parse', methods=['POST'])
def parse():
    json_input = request.form['data']
    text, fixed_deps = process_json_input(json_input)
    result = parser.parse_tagged_text(text.encode('cp874', 'ignore'), fixed_deps=fixed_deps)
    return json.dumps({'result':result.decode('cp874')})

if __name__ == '__main__':
    app.run()
