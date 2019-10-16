#!/usr/bin/env python3

"""
    Tool for creating a glossary for a lecture.
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

infile = os.path.realpath(os.path.abspath(args.INFILE))
mathhub_dir = harvest.get_mathhub_dir(infile)
restpath = os.path.relpath(infile, mathhub_dir).split(os.sep)
if "source" not in restpath:
    raise Exception("Couldn't find a 'source' folder in " + infile)
root_repo = os.sep.join(restpath[:restpath.index("source")])
root_doc = os.sep.join(restpath[restpath.index("source")+1:])
if root_doc.endswith(".tex"):
    root_doc = root_doc[:-4]

print("Mathhub: " + mathhub_dir)
print("root repo: " + root_repo)
print("root doc: " + root_doc)

mygraph = graph.Graph()
graph.fill_graph(mathhub_dir, root_repo, root_doc, mygraph, False)


lang = "en"
logger = harvest.SimpleLogger(0)   # for now: 0 verbosity
ctx = harvest.HarvestContext(logger, harvest.DataGatherer(), mathhub_dir)
ctx.repo = "UNKOWN_REPO"
ctx.gatherer.push_repo("UNKNOWN_REPO", ctx)    # we don't really care, do we?

for filename in mygraph.g_nodes:
    root, name = os.path.split(filename)
    harvest.harvest_file(root, name, ctx)

    
glossary = Glossary(lang, mathhub_dir)
glossary.fill(ctx.gatherer, allowunknownlang=True)

with open(args.OUTFILE, "w") as fp:
    fp.write(str(glossary))
