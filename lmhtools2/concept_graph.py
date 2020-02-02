''' Tool for generating lecture graph '''

from lmh_harvest import *
from lmh_logging import *
from lmh_elements import *

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



# node : { 'title':..., 'covered':...}
nodes = { }

# edge : { 'type':..., 'from':..., 'to':,... }
all_edges = { }

edge_list = []


def dfs(x):
    node = x
    if node in nodes:
        return
    if isinstance(node, LmhFile):
        nodes[node] = {'title' : node.position.filename, 'covered' : not dfs.reached_eoc}
    elif isinstance(node, OMGROUP):
        nodes[node] = {'title' : node.title, 'covered' : not dfs.reached_eoc}
    else:
        print('Unexpected node type:', node)
        return
    # for c in x.collect_children([OMGROUP, USEMHMODULE, GIMPORT, GUSE, IMPORTMHMODULE, MHINPUTREF]):
    for child in x.children:   # avoid blocking if x is an omgroup
        for c in child.collect_children([OMGROUP, GIMPORT, IMPORTMHMODULE, MHINPUTREF, COVEREDUPTOHERE]):
            if isinstance(c, COVEREDUPTOHERE):
                dfs.reached_eoc = True
                continue
            if isinstance(c, OMGROUP):
                all_edges[c] = { 'type':'omgroup', 'from':node, 'to':c }
                edge_list.append(c)
                dfs(c)
                continue
            to = c.target_file
            # if isinstance(c, GUSE) or isinstance(c, USEMHMODULE):
            #     all_edges[c] = { 'type':'use', 'from':node, 'to':c }
            # else:
            all_edges[c] = { 'type':'normal', 'from':node, 'to':to }
            edge_list.append(c)
            dfs(to)
dfs.reached_eoc = False  # end of coverage

dfs(root_lmhfile)


# json = {'nodes':[], 'edges':[], 'chapters':[]}
jsongraph = {'nodes':[], 'edges':[]}


for node in nodes:
    if isinstance(node, LmhFile) and len(node.children) == 1 and isinstance(node.children[0], OMGROUP):
        continue

    if isinstance(node, OMGROUP):
        color = '#000099' if nodes[node]['covered'] else '#8888ff'
    else:
        color = '#009900' if nodes[node]['covered'] else '#88ff88'

    jsongraph['nodes'].append({
            'id' : str(node),
            'color' : color,
            'label' : nodes[node]['title']
        })

for edge in all_edges:
    source = all_edges[edge]['from']
    if isinstance(source, LmhFile) and len(source.children) == 1 and isinstance(source.children[0], OMGROUP):
        continue
    target = all_edges[edge]['to']
    if isinstance(target, LmhFile) and len(target.children) == 1 and isinstance(target.children[0], OMGROUP):
        target = target.children[0]

    jsongraph['edges'].append({
            'id' : str(edge),
            'style': 'include',
            'from': str(source),
            'to': str(target),
            'label': ''
        })


import json
with open('graph.json', 'w') as fp:
    fp.write(json.dumps(jsongraph, indent=4))


