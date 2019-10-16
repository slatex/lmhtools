#!/usr/bin/env python3

"""
    Tool for creating a glossary for a lecture.

    What it should be doing (not yet implemented like this):
        Collect all trefis/defis/trefis that are displayed in the document (i.e. following inputrefs etc.)
        Use them as keys in the glossary and find their definitions (somehow)
"""

import os
import lmh_harvest as harvest
import import_graph as graph
from make_glossary import *

import argparse

parser = argparse.ArgumentParser(description="Script for generating a glossary for a lecture")
parser.add_argument("INFILE", help=".tex file for which the glossary shall be generated (typically path/to/notes.tex)")
parser.add_argument("OUTFILE", help="output file")
args = parser.parse_args()

mathhub_dir = harvest.get_mathhub_dir(args.INFILE)
root_repo, root_doc = harvest.split_path_repo_doc(args.INFILE)

print("Mathhub: " + mathhub_dir)
print("root repo: " + root_repo)
print("root doc: " + root_doc)

def getdefisandtrefis():
    displayedgraph = graph.Graph()
    displayedfiles = graph.add_omgroup_data(mathhub_dir, root_repo, root_doc, displayedgraph, False)
    displayedfiles += displayedgraph.module_nodes

    logger = harvest.SimpleLogger(2)
    ctx = harvest.HarvestContext(logger, harvest.DataGatherer(), mathhub_dir)

    newfiles = displayedfiles[:]
    while newfiles:
        for filename in newfiles:
            if not os.path.isfile(filename):
                print("File " + filename + " doesn't exist")
                continue
            ctx.repo = harvest.split_path_repo_doc(filename)[1]
            ctx.gatherer.push_repo(ctx.repo, ctx)
            root, name = os.path.split(filename)
            harvest.harvest_file(root, name, ctx)
        
        newfiles = []
        for inp in ctx.gatherer.mhinputrefs:
            destfile = inp["dest_path"]
            if destfile not in displayedfiles:
                newfiles.append(destfile)
                displayedfiles.append(destfile)

    return (ctx.gatherer.defis, ctx.gatherer.trefis)

defis, trefis = getdefisandtrefis()

# Now we need to gather everything imported to find definitions for trefis

logger = harvest.SimpleLogger(2)

mygraph = graph.Graph()
graph.fill_graph(mathhub_dir, root_repo, root_doc, mygraph, False)


lang = "en"
ctx = harvest.HarvestContext(logger, harvest.DataGatherer(), mathhub_dir)

for filename in list(mygraph.g_nodes.keys()) + list(mygraph.module_nodes.keys()) + [k[0] for k in mygraph.omgroup_nodes.keys()]:
    ctx.repo = harvest.split_path_repo_doc(filename)[1]
    ctx.gatherer.push_repo(ctx.repo, ctx)
    root, name = os.path.split(filename)
    harvest.harvest_file(root, name, ctx)


    
glossary = Glossary(lang, mathhub_dir)
# glossary.fill(ctx.gatherer, allowunknownlang=True)

for defi in defis:
    glossary.fillDefi(defi)

defiIndex = {}

for defi in ctx.gatherer.defis:
    defiIndex[(defi["mod_name"], defi["name"])] = defi

print(defiIndex)

for trefi in trefis:
    k = (trefi["target_mod"], trefi["name"])
    if k not in defiIndex:
        print("Failed to find definition for trefi " + k[0] + "?" + k[1] + " in " + trefi["path"])
        continue
    glossary.fillDefi(defiIndex[k])


with open(args.OUTFILE, "w") as fp:
    fp.write(str(glossary))
