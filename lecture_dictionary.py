#!/usr/bin/env python3

"""
    Tool for creating a dictionary for a lecture.
"""

import os
import lmh_harvest as harvest
import import_graph as graph
from make_dictionary import *

import argparse

parser = argparse.ArgumentParser(description="Script for generating a dictionary for a lecture")
parser.add_argument("INFILE", help=".tex file for which the dictionary shall be generated (typically path/to/notes.tex)")
parser.add_argument("OUTFILE", help="output file")
args = parser.parse_args()

mathhub_dir = harvest.get_mathhub_dir(args.INFILE)
root_repo, root_doc = harvest.split_path_repo_doc(args.INFILE)


ONLY_COVERED_PART = True

print("Mathhub: " + mathhub_dir)
print("root repo: " + root_repo)
print("root doc: " + root_doc)

def getdefisandtrefis():
    displayedgraph = graph.Graph()
    displayedfiles = graph.add_omgroup_data(mathhub_dir, root_repo, root_doc, displayedgraph, ONLY_COVERED_PART)
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
graph.fill_graph(mathhub_dir, root_repo, root_doc, mygraph, ONLY_COVERED_PART)


lang = "en"
ctx = harvest.HarvestContext(logger, harvest.DataGatherer(), mathhub_dir)

relevantfiles = \
        list(mygraph.g_nodes.keys()) +\
        list(mygraph.module_nodes.keys()) +\
        [k[0] for k in mygraph.omgroup_nodes.keys()]

print("\n".join(relevantfiles))

extrafiles = []
for filename in relevantfiles:
    # check computer.en.tex if computer.tex is used
    lf = filename[:-4]+".en.tex"
    if os.path.isfile(lf):
        extrafiles.append(lf)
    lf = filename[:-4]+".de.tex"
    if os.path.isfile(lf):
        extrafiles.append(lf)

for filename in relevantfiles + extrafiles:
    ctx.repo = harvest.split_path_repo_doc(filename)[1]
    ctx.gatherer.push_repo(ctx.repo, ctx)
    root, name = os.path.split(filename)
    harvest.harvest_file(root, name, ctx)


    
dictionary = Dictionary(["en", "de"], mathhub_dir)
relevantsymbs = []
for e in defis + trefis:
    symb = (e["mod_name"], e["name"])
    relevantsymbs.append(symb)

for defi in ctx.gatherer.defis:
    symb = (defi["mod_name"], defi["name"])
    if symb in relevantsymbs:
        lang = defi["lang"]
        if lang == "?":   # in monolingual module
            lang = "en"
        dictionary.addEntry(symb, lang, defi["string"])

with open(args.OUTFILE, "w") as fp:
    fp.write(getAsLaTeX(dictionary))
