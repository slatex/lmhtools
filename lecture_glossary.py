#!/usr/bin/env python3

"""
    Tool for creating a glossary for a lecture.
"""

import os
import lmh_harvest as harvest
import import_graph as graph
from make_glossary import *


mathhub_dir = "/home/jfs/mmt/content/MathHub"
root_repo = "MiKoMH/IWGS"
root_doc = "course/notes/notes"

mygraph = graph.Graph()
graph.fill_graph(mathhub_dir, root_repo, root_doc, mygraph, False)


print(mygraph.module_nodes)
print(mygraph.g_nodes)


lang = "en"
logger = harvest.SimpleLogger(0)   # for now: 0 verbosity
ctx = harvest.HarvestContext(logger, harvest.DataGatherer(), mathhub_dir)
ctx.repo = "UNKOWN_REPO"
ctx.gatherer.push_repo("UNKNOWN_REPO", ctx)    # we don't really care, do we?

for filename in mygraph.g_nodes:
    print(filename)
    root, name = os.path.split(filename)
    harvest.harvest_file(root, name, ctx)

print(ctx.gatherer.defis)
    
glossary = Glossary(lang, mathhub_dir)
glossary.fill(ctx.gatherer, allowunknownlang=True)
print(glossary)
