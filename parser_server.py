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

def traverse(node, nodes=[]):
    nodes.append([(node['snode'][0]['s'], node['snode'][0]['e']), node['snode'][0]['text'], node['pos']])
    for child in node['children']:
        traverse(child, nodes)
    nodes.sort()
    return nodes

def parse_sstc(json_input):
    json_obj = json.loads(json_input)
    root = json_obj['sstc']['tree'][0]
    nodes = traverse(root, [])
    return ' '.join(map(lambda x: x[1]+'/'+x[2], nodes)), map(lambda x:x[0], nodes)

def parse_fixed_deps(json_input):
    json_obj = json.loads(json_input)
    fixed_deps = []
    for dep in json_obj['differences']:
        node = tuple(map(int, dep['id'].split('-')))
        if dep['parent'] != 'root':
            fixed_deps.append((tuple(map(int, dep['parent'].split('-'))), node))
        else:
            fixed_deps.append(('root', node))
    return fixed_deps

def process_json_input(json_input):
    text, nodes = parse_sstc(json_input)
    nodes.insert(0,'root')
    fixed_deps = parse_fixed_deps(json_input)
    fixed_deps = map(lambda x: (nodes.index(x[0]), nodes.index(x[1])), fixed_deps)
    return text, fixed_deps

@app.route('/parse', methods=['POST'])
def parse():
    json_input = request.form['data']
    text, fixed_deps = process_json_input(json_input)
    print 'fixed_deps'
    print text
    print fixed_deps
    result = parser.parse_tagged_text(text.encode('cp874', 'ignore'), fixed_deps=fixed_deps)
    return json.dumps({'result':result.decode('cp874')})

if __name__ == '__main__':
    app.run()
