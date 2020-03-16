#!/usr/bin/env python3

''' Tool for generating lecture graph '''

from lmh_harvest import *
from lmh_logging import *
from lmh_elements import *
import regexes
import re

import os
import sys

root_doc = os.path.realpath(os.path.abspath(sys.argv[1]))
mh = get_mathhub_dir(root_doc)

harvester = Harvester(Logger(2), mh)

harvester.load_files('^((smglom)|(MiKoMH))/.*$')

harvester.ctx.referencer.compile()

root_lmhfile = None
for f in harvester.files:
    if f.path == root_doc:
        root_lmhfile = f

if not f:
    print(f'It seems like {root_doc} wasn\'t processed during harvesting')
    sys.exit(1)



# # node : { 'title':..., 'covered':...}
# nodes = { }
# 
# # edge : { 'type':..., 'from':..., 'to':,... }
# all_edges = { }
# 
# edge_list = []

nodes = {}

class Node(object):
    def __init__(self, texnode, covered):
        self.texnode = texnode
        self.covered = covered

        self.outedges = []
        self.inedges = []
        self.alive = True

        if self.isomgroup():
            self.title = self.texnode.title
        else:
            self.title = self.texnode.position.toString(short=True)

    def isomgroup(self):
        return isinstance(self.texnode, OMGROUP)

    def get_id(self):
        return self.texnode.position.toString(short=True)

class Edge(object):
    def __init__(self, source, target, number, texnode):
        self.source = source
        self.target = target
        self.number = number
        self.texnode = texnode

    def get_id(self):
        return self.source.get_id() + ';' + (self.texnode.position.toString(short=True) if self.texnode else '-') + ';' + self.target.get_id()


all_edges = []


def dfs(node):
    if node in nodes:
        return
    if isinstance(node, LmhFile) or isinstance(node, OMGROUP):
        if isinstance(node, OMGROUP) and node.isblind:
            print('skipping', node, node.match.group(0))
            return
        nodes[node] = Node(node, not dfs.reached_eoc)
    else:
        print('Unexpected node type:', node)
        return

    for child in node.children:   # avoid blocking if node is an omgroup
        for c in child.collect_children([OMGROUP, GIMPORT, IMPORTMHMODULE, MHINPUTREF, COVEREDUPTOHERE]):
            if isinstance(c, COVEREDUPTOHERE):
                dfs.reached_eoc = True
                continue
            if isinstance(c, OMGROUP):
                # all_edges[c] = { 'type':'omgroup', 'from':node, 'to':c }
                e = Edge(node, c, dfs.counter, c)
                dfs.counter += 1
                all_edges.append(e)
                dfs(c)
                continue
            to = c.target_file
            edge = Edge(node, to, dfs.counter, c)
            dfs.counter += 1
            all_edges.append(edge)
            if not to:
                print('Failed to find: ' + c.target_position.toString())
                print('Unresolved target in: ' + c.position.toString())
                print(c.match.group(0))
                continue
            dfs(to)
dfs.reached_eoc = False  # end of coverage
dfs.counter = 0

dfs(root_lmhfile)


# fill in edges:
for e in all_edges:
    if not e.target: continue  # edges that couldn't be resolved
    if isinstance(e.target, OMGROUP) and e.target.isblind: continue  # blindomgroups are skipped (frontmatter)
    e.target = nodes[e.target]
    e.source = nodes[e.source]
    e.target.inedges.append(e)
    e.source.outedges.append(e)

all_edges = None    # don't use this list anymore

# merge edges of shape omgroup -> file with single omgroup -> that single omgroup
for node in nodes.values():
    if isinstance(node.texnode, LmhFile) and len(node.texnode.children) == 1 and isinstance(node.texnode.children[0], OMGROUP) and node.texnode.children[0] in nodes:
        node.alive = False
        for e in node.inedges:
            e.target = nodes[node.texnode.children[0]]
            e.texnode = None
        assert len(nodes[node.texnode.children[0]].inedges) == 1
        nodes[node.texnode.children[0]].inedges = node.inedges




# json = {'nodes':[], 'edges':[], 'chapters':[]}
jsongraph = {'nodes':[], 'edges':[], 'chapters':[]}

actualnodes = set()


ADD_SREFS = True

for node in nodes.values():
    if not node.alive:
        continue
# WE HAVE TO SHOW OMGROUPS TO HAVE EDGES TO THEM
    if node.isomgroup() and not ADD_SREFS:
        continue
    if node.texnode == root_lmhfile:
        continue

    actualnodes.add(node)

    color = '#00ff00' if node.covered else '#0000ff'

    jsongraph['nodes'].append({
            'id' : node.get_id(),
            'color' : color,
            'label' : node.title
        })

    for edge in node.outedges:
        jsongraph['edges'].append({
            'id' : edge.get_id(),
            'style' : 'include',
            'from' : edge.source.get_id(),
            'to' : edge.target.get_id(),
            'label' : '',
            })

# ADD SREFS (ONLY THE ONES INTO OMGROUPS WILL WORK)
if ADD_SREFS:
    nodeidmap = {}
    for node in actualnodes:
        if not node.isomgroup(): continue
        id_ = node.texnode.position.modname
        if not id_: continue
        nodeidmap[id_] = node
    for node in actualnodes:
        for match in re.finditer(regexes.re_sref, node.texnode.get_content()):
            id_ = match.group('arg')
            print('id:', id_)
            if id_ not in nodeidmap: continue  # this is quite possible, since refs can be to examples, definitions, ...
            print('YES')
            jsongraph['edges'].append({
                'id' : 'sref:' + node.get_id() + ';' + nodeidmap[id_].get_id(),
                'style' : 'reference',
                'from' : node.get_id(),
                'to' : nodeidmap[id_].get_id(),
                'label' : '',
                })


def chapterdfs(node, j, depth, l):
    assert isinstance(node, Node)
    if node in chapterdfs.placed:
        return
    chapterdfs.placed.add(node)
    if depth <= 0:
        l.append(node.get_id())
        for child in node.outedges:
            chapterdfs(child.target, j, 0, l)
    elif depth == 1:
        l.append('c.' + node.get_id())
        l2 = []
        j['chapters'].append({
                'id': 'c.' + node.get_id(),
                'chapters' : [],
                'nodes' : l2,
                'label' : node.title,
                'highlevel' : node.isomgroup() or node.texnode == root_lmhfile,
            })
        if node in actualnodes:
            l2.append(node.get_id())
        for child in node.outedges:
            chapterdfs(child.target, j, 0, l2)
    else:
        l.append('c.' + node.get_id())
        l2 = []
        l3 = []
        j['chapters'].append({
                'id': 'c.' + node.get_id(),
                'chapters' : l2,
                'nodes' : l3,
                'label' : node.title,
                'highlevel' : node.isomgroup() or node.texnode == root_lmhfile,
            })
        if node in actualnodes:
            l3.append(node.get_id())
        for child in node.outedges:
            chapterdfs(child.target, j, depth-1, l2)

# nodes already put into chapters
chapterdfs.placed = set()

chapterdfs(nodes[root_lmhfile], jsongraph, 8, [])

import json
with open('graph.json', 'w') as fp:
    fp.write(json.dumps(jsongraph, indent=4))


