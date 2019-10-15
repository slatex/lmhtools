#!/usr/bin/env python3

"""
    Tool to create a concept graph for sTeX-based lectures.
    The output is intended for TGView.
    The graph construction code has been moved to `import_graph.py`.
"""

import sys
import os
import lmh_harvest as harvest
from import_graph import *

def get_json(covered_graph, full_graph, mathhub_dir, with_omgroups=True, with_modules=True, with_g_edges=True, with_text=True):
    json_graph = {"nodes" : [], "edges" : []}
    to_relpath = lambda path : os.path.relpath(path, start=mathhub_dir)
    omgr2id = lambda omgr : to_relpath(omgr[0]) + "?" + omgr[1]
    covered_onodes = list(covered_graph.omgroup_nodes.keys())
    covered_mnodes = list(covered_graph.module_nodes.keys()) 
    covered_gnodes = list(covered_graph.g_nodes.keys())

    if with_omgroups:
        for node in full_graph.omgroup_nodes.keys():
            json_graph["nodes"].append({
                "id" : omgr2id(node),
                "color" : "#222222" if node in covered_onodes else "#cccccc",
                "label" : full_graph.omgroup_nodes[node]["label"] })
        for start,end in full_graph.omgroup_edges:
            json_graph["edges"].append({
                "id" : omgr2id(start) + "??" + omgr2id(end),
                "style" : "include",
                "to" : omgr2id(start),
                "from" : omgr2id(end),
                "label" : ""})
    if with_omgroups and with_modules:
        for start,end in full_graph.omgroup2module_edges:
            if end in full_graph.module_nodes:
                json_graph["edges"].append({
                    "id" : omgr2id(start) + "??" + to_relpath(end),
                    "style" : "include",
                    "to" : omgr2id(start),
                    "from" : to_relpath(end),
                    "label" : ""})

    if with_modules:
        for node in full_graph.module_nodes:
            if full_graph.module_nodes[node]["type"] == "text" and not with_text:
                continue
            if full_graph.module_nodes[node]["type"] == "text":
                json_graph["nodes"].append({
                        "id" : to_relpath(node),
                        "color" : "#ff8800" if node in covered_mnodes else "#ffeecc",
                        "label" : full_graph.module_nodes[node]["label"]})
            else:
                json_graph["nodes"].append({
                        "id" : to_relpath(node),
                        "color" : "#0000ff" if node in covered_mnodes else "#ddddff",
                        "label" : full_graph.module_nodes[node]["label"]})
        for start,end in full_graph.module_edges:
            assert start in full_graph.module_nodes
            assert end in full_graph.module_nodes
            if not with_text and (full_graph.module_nodes[start]["type"]=="text" or full_graph.module_nodes[end]["type"]=="text"):
                continue
            json_graph["edges"].append({
                "id" : to_relpath(start) + "??" + to_relpath(end),
                "style" : "include",
                "to" : to_relpath(start),
                "from" : to_relpath(end),
                "label" : ""})

    if with_g_edges:
        for node in full_graph.g_nodes.keys():
            json_graph["nodes"].append({
                "id" : to_relpath(node),
                "color" : "#00cc00" if node in covered_gnodes else "#cceecc",
                "label" : full_graph.g_nodes[node]["label"]})
        for start,end in full_graph.g_edges.keys():
            assert start in full_graph.module_nodes.keys() or start in full_graph.g_nodes.keys()
            if start in full_graph.module_nodes.keys() and full_graph.module_nodes[start]["type"]=="text" and not with_text:
                continue
            if end in full_graph.module_nodes.keys() or end in full_graph.g_nodes.keys():
                json_graph["edges"].append({
                    "id" : to_relpath(start) + "??" + to_relpath(end),
                    "style" : {"import":"include","use":"uses"}[full_graph.g_edges[(start,end)]["type"]],
                    "to" : to_relpath(start),
                    "from" : to_relpath(end),
                    "label" : ""})
    return json_graph


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Script for generating a TGView-compatible concept graph from sTeX")
    parser.add_argument("-i", "--ignoretoc", action="store_true", help="Ignore table of contents (omgroups)")
    parser.add_argument("-n", "--notext", action="store_true", help="Ignore text nodes")
    parser.add_argument("DIRECTORY", help=".tex file for which the graph shall be generated (typically path/to/notes.tex)")
    args = parser.parse_args()

    ## Split path into components
    mathhub_dir = os.path.abspath(args.DIRECTORY)
    root_doc = None
    while not mathhub_dir.endswith("source"):
        new_path, head = os.path.split(mathhub_dir)
        if not root_doc:
            if not head.endswith(".tex"):
                raise Exception("Expected a *.tex file")
            root_doc = head[:-4]
        else:
            root_doc = head + "/" + root_doc
        if new_path == mathhub_dir:
            raise Exception("Failed to understand path (no source folder found)")
        mathhub_dir = new_path

    mathhub_dir = os.path.split(mathhub_dir)[0]  # pop source dir
    root_repo = []
    while not mathhub_dir.endswith("MathHub"):
        new_path, head = os.path.split(mathhub_dir)
        root_repo = [head] + root_repo
        if new_path == mathhub_dir:
            raise Exception("Failed to infer MathHub directory")
        mathhub_dir = new_path
    root_repo = "/".join(root_repo)

    print("Mathhub: " + mathhub_dir)
    print("root repo: " + root_repo)
    print("root doc: " + root_doc)

    covered_graph = Graph()
    fill_graph(mathhub_dir, root_repo, root_doc, covered_graph, True)
    
    full_graph = Graph()
    fill_graph(mathhub_dir, root_repo, root_doc, full_graph, False)
    
    json_graph = get_json(covered_graph, full_graph, mathhub_dir, with_omgroups=(not args.ignoretoc), with_text=(not args.notext))
    
    import json
    with open("graph.json", "w") as fp:
        fp.write(json.dumps(json_graph, indent=4))

