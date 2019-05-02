#!/usr/bin/env python3

"""
Very hacky and unpolished script to create a concept graph for the AI lecture
"""

import sys
import re
import os
import smglom_harvest as harvest


### PART 1 : PARSING OMGROUPS AND MHINPUTREFS

def parse(string, regexes):
    """
    Assumes that regexes is a list of pairs (regex, token_type).
    Returns tokens from a string as pairs (match, token_type),
    sorted according to the match start.
    """
    tokens = []
    for (regex, token_type) in regexes:
        tokens += [(match, token_type) for match in re.finditer(regex, string)]
    return sorted(tokens, key = lambda e : e[0].start())




class Context(object):
    def __init__(self, mathhub, repo, doc, onlycovered = False):
        self.mathhub = mathhub
        self.repo = [repo]
        self.doc = [doc]
        self.inmod = False
        self.files = [(repo, doc)]
        self.file2mod = []
        self.mhinputrefs = []   # mod 2 file
        self.onlycovered = onlycovered

    def get_path(self):
        return os.path.join(self.mathhub, self.repo[-1], "source", self.doc[-1]) + ".tex"
    
    def throw(self, message):
        print(f"{self.get_path()}: {message}")

    def push_mhinputref(self, repo, doc):
        if self.inmod:
            self.mhinputrefs.append((self.repo[-1], self.doc[-1], self.file2mod[-1], repo, doc))
        else:
            self.mhinputrefs.append((self.repo[-1], self.doc[-1], None, repo, doc))
        return (repo, doc) not in self.files


    def push_doc(self, repo, doc):
        if (repo, doc) in self.files:
            raise Exception(f"Cycle detected (reached {(repo, doc)} before)")

        self.repo.append(repo)
        self.doc.append(doc)
        self.files.append((repo, doc))
    
    def pop(self):
        self.repo.pop()
        self.doc.pop()

    def push_mod(self, id_, title, type_):
        if not id_:
            id_ = title.replace(" ", "-")
        self.file2mod.append((self.repo[-1], self.doc[-1], id_, title, type_))
        self.inmod = True

    def pop_mod(self):
        self.inmod = False



TOKEN_MHINPUTREF       = 0
TOKEN_BEGIN_OMGROUP    = 1
TOKEN_END_OMGROUP      = 2
TOKEN_COVEREDUPTOHERE  = 3


re_arg_core = r"(?:[^\{\}\$]|(?:\$[^\$]+\$)|(\{[^\{\}\$]*\}))+"
re_arg = r"\{(?P<arg>" + re_arg_core + r")\}\s*"
re_param = r"(?:\[(?P<params>[^\]]*)\])?\s*"

re_mhinputref       = re.compile(r"\\mhinputref\*?" + re_param + re_arg)
re_begin_omgroup    = re.compile(r"\\begin\{omgroup\}" + re_param + re_arg)
re_end_omgroup      = re.compile(r"\\end\{omgroup\}")
re_covereduptohere = re.compile(r"\\covereduptohere")

regexes = [
        (re_mhinputref, TOKEN_MHINPUTREF),
        (re_begin_omgroup, TOKEN_BEGIN_OMGROUP),
        (re_end_omgroup, TOKEN_END_OMGROUP),
        (re_covereduptohere, TOKEN_COVEREDUPTOHERE),
        ]

class CoveredUntilHereException(Exception):
    pass

def recurse_omgroup(context, i, tokens):
    (match, token_type) = tokens[i]
    assert token_type == TOKEN_BEGIN_OMGROUP
    params = harvest.get_params(match.group("params"))
    if "id" in params:
        id_ = params["id"]
    else:
        id_ = None
    title = match.group("arg")
    context.push_mod(id_, title, "omgroup")
    i += 1
    recurse_into = []
    found_end = False
    while i < len(tokens):
        (match, token_type) = tokens[i]
        if token_type == TOKEN_END_OMGROUP:
            i += 1
            found_end = True
            break
        elif token_type == TOKEN_MHINPUTREF:
            repo = match.group("params")
            if repo:
                assert "," not in repo and "=" not in repo
            else:
                repo = context.repo[-1]
            doc = match.group("arg")
            context.push_mhinputref(repo, doc)
            recurse_into.append((repo, doc))
            i += 1
        elif token_type == TOKEN_COVEREDUPTOHERE:
            if context.onlycovered:
                raise CoveredUntilHereException()
            i += 1
        else:
            context.throw(f"Unexpected token: '{match.group(0)}'")
            i += 1

    if not found_end:
        context.throw("Missing \\end{omgroup}")

    context.pop_mod()
    for (repo, doc) in recurse_into:
        if (repo, doc) not in context.files:
            context.push_doc(repo, doc)
            recurse_file(context)
    return i
        

def recurse_file(context):
    if not os.path.isfile(context.get_path()):
        context.throw("File not found: " + context.get_path())
        context.pop()
        return
    with open(context.get_path()) as fp:
        string = harvest.preprocess_string(fp.read())
        tokens = parse(string, regexes)
        i = 0
        while i < len(tokens):
            (match, token_type) = tokens[i]
            if token_type == TOKEN_BEGIN_OMGROUP:
                i = recurse_omgroup(context, i, tokens)
            else:
                context.throw(f"Unexpected token: '{match.group(0)}'")
                i += 1
        else:
            pass

    context.pop()

### PART 2 : COLLECTING GRAPH DATA

class Graph(object):
    def __init__(self):
        # values are dictionaries for extra info
        self.omgroup_nodes = {}    # (file, title) : { }
        self.omgroup_edges = {}
        self.module_nodes = {}
        self.module_edges = {}
        self.omgroup2module_edges = {}
        self.g_nodes = {}
        self.g_edges = {}

def add_omgroup_data(mathhub, root_repo, root_doc, graph, onlycovered):
    # gather data
    context = Context(mathhub, root_repo, root_doc, onlycovered)
    try:
        recurse_file(context)
    except CoveredUntilHereException:
        pass

    # process data
    file2omgroups = {}
    for entry in context.file2mod:
        if entry[4] == "omgroup":
            key = (entry[0], entry[1])
            if key not in file2omgroups:
                file2omgroups[key] = []
            file2omgroups[key].append((entry[0], entry[1], entry[2], entry[3]))  # repo, doc, id, title

    omgroup2files = {}
    for entry in context.mhinputrefs:
        if entry[2]:
            key = (entry[2][0], entry[2][1], entry[2][2], entry[2][3])
            if key not in omgroup2files:
                omgroup2files[key] = []
            omgroup2files[key].append((entry[3], entry[4]))
        else:
            print("Skipping:", repr(entry))

    omgroup2files[(root_repo, root_doc, "root", "AI Lecture")] = [(root_repo, root_doc)]


    # find fringe
    potential_modules = []
    for v in omgroup2files.values():
        for e in v:
            if e not in file2omgroups:
                e2 = os.path.join(mathhub, e[0], "source", e[1]) + ".tex"
                potential_modules.append(e2)


    # graph data
    omgr2path = lambda omgr : os.path.join(mathhub, omgr[0], "source", omgr[1]) + ".tex"
    for omgroup in omgroup2files.keys():
        node = (omgr2path(omgroup), omgroup[2])
        graph.omgroup_nodes[node] = {
                    "label" : omgroup[3],
                }
        for f in omgroup2files[omgroup]:
            if f in file2omgroups:
                for omg2 in file2omgroups[f]:
                    graph.omgroup_edges[((omgr2path(omgroup), omgroup[2]), (omgr2path(omg2), omg2[2]))] = { }
            else:
                path = os.path.join(mathhub, f[0], "source", f[1]) + ".tex"
                graph.omgroup2module_edges[(node, path)] = {
                            "status" : "unconfirmed",       # not clear if module exists
                        }

    return potential_modules

def fill_graph(mathhub, root_repo, root_doc, graph, onlycovered = False):
    potential_modules = add_omgroup_data(mathhub, root_repo, root_doc, graph, onlycovered)
    blocked_nodes = potential_modules[:]

    logger = harvest.SimpleLogger(2)
    potential_nodes = {}
    potential_edges = []
    gimports = []
    while potential_modules:
        gatherer = harvest.DataGatherer()
        context = harvest.HarvestContext(logger, gatherer, mathhub)
        for pm in potential_modules:
            context.repo = "/".join(pm.split("/")[:mathhub.count("/")+3]) # TODO: platform independence
            path = pm
            root, filename = os.path.split(path)
            try:
                harvest.harvest_file(root, filename, context)
            except FileNotFoundError:
                print("couldn't find '" + path + "'")
        for mod in gatherer.modules:
            node = mod["path"]
            if node not in potential_nodes.keys():
                name = mod["mod_name"]
                if not name:
                    name = os.path.split(node)[1][:-4]
                potential_nodes[node] = {"label" : name, "type" : "module"}
        for file_ in gatherer.textfiles:
            node = file_["path"]
            if node not in potential_nodes.keys():
                potential_nodes[node] = {"label" : os.path.split(node)[1], "type" : "text"}
        assert not gatherer.sigfiles
        assert not gatherer.langfiles

        potential_modules = []      # includes text files
        for imp in gatherer.importmhmodules:
            destnode = imp["dest_path"]
            if destnode not in blocked_nodes:
                blocked_nodes.append(destnode)
                potential_modules.append(destnode)
            potential_edges.append((imp["path"], destnode))
        for gimport in gatherer.gimports:
            gimports.append((gimport["path"],
                             os.path.join(gimport["dest_repo"], "source", gimport["dest_mod"]) + ".tex"))
            graph.g_edges[gimports[-1]] = {}

    for node in potential_nodes.keys():
        graph.module_nodes[node] = {
                    "label" : potential_nodes[node]["label"],
                    "type" : potential_nodes[node]["type"],
                }

    for start, end in potential_edges:
        if start in potential_nodes.keys() and end in potential_nodes.keys():
            graph.module_edges[(start, end)] = {}

    ## handle gimports
    assert graph.g_nodes == {}
    while gimports:
        gatherer = harvest.DataGatherer()
        context = harvest.HarvestContext(logger, gatherer, mathhub)
        for source, dest in gimports:
            if dest not in graph.g_nodes.keys() and dest not in potential_nodes.keys():
                context.repo = "/".join(dest.split("/")[:mathhub.count("/")+3]) # TODO: platform independence
                root, filename = os.path.split(dest)
                try:
                    harvest.harvest_file(root, filename, context)
                except FileNotFoundError:
                    print("couldn't find '" + path + "'")
        assert not gatherer.langfiles
        assert not gatherer.textfiles
        for mod in gatherer.modules + gatherer.sigfiles:
            node = mod["path"]
            if node not in potential_nodes.keys() and node not in graph.g_nodes.keys():
                name = mod["mod_name"]
                if not name:
                    name = os.path.split(node)[1][:-4]
                graph.g_nodes[node] = {"label" : name, "type" : "module"}
        gimports = []
        for gimport in gatherer.gimports:
            pair = (gimport["path"], os.path.join(gimport["dest_repo"], "source", gimport["dest_mod"]) + ".tex")
            graph.g_edges[pair] = {}
            if pair[1] not in graph.g_nodes.keys() and pair[1] not in potential_nodes.keys():
                gimports.append(pair)





def get_json(coverd_graph, full_graph, with_omgroups=True, with_modules=True, with_gimports=True, with_text=True):
    json_graph = {"nodes" : [], "edges" : []}
    omgr2id = lambda omgr : omgr[0] + "?" + omgr[1]
    covered_nodes = list(covered_graph.omgroup_nodes.keys())
    covered_nodes += list(covered_graph.module_nodes.keys()) 
    covered_nodes += list(covered_graph.g_nodes.keys())

    if with_omgroups:
        for node in full_graph.omgroup_nodes.keys():
            json_graph["nodes"].append({
                "id" : omgr2id(node),
                "color" : "#222222" if node in covered_nodes else "#cccccc",
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
                    "id" : omgr2id(start) + "??" + end,
                    "style" : "include",
                    "to" : omgr2id(start),
                    "from" : end,
                    "label" : ""})

    if with_modules:
        for node in full_graph.module_nodes:
            if full_graph.module_nodes[node]["type"] == "text" and not with_text:
                continue
            if with_text:
                json_graph["nodes"].append({
                        "id" : node,
                        "color" : "#ff8800" if node in covered_nodes else "#ffeecc",
                        "label" : full_graph.module_nodes[node]["label"]})
            else:
                json_graph["nodes"].append({
                        "id" : node,
                        "color" : "#0000ff" if node in covered_nodes else "#ddddff",
                        "label" : full_graph.module_nodes[node]["label"]})
        for start,end in full_graph.module_edges:
            assert start in full_graph.module_nodes
            assert end in full_graph.module_nodes
            if not with_text and (full_graph.module_nodes[start]["type"]=="text" or full_graph.module_nodes[end]["type"]=="text"):
                continue
            json_graph["edges"].append({
                "id" : start + "??" + end,
                "style" : "include",
                "to" : start,
                "from" : end,
                "label" : ""})

    if with_gimports:
        for node in full_graph.g_nodes.keys():
            json_graph["nodes"].append({
                "id" : node,
                "color" : "#00cc00" if node in covered_nodes else "#cceecc",
                "label" : full_graph.g_nodes[node]["label"]})
        for start,end in full_graph.g_edges.keys():
            assert start in full_graph.module_nodes.keys() or start in full_graph.g_nodes.keys()
            if end in full_graph.module_nodes.keys() or end in full_graph.g_nodes.keys():
                json_graph["edges"].append({
                    "id" : start + "??" + end,
                    "style" : "include",
                    "to" : start,
                    "from" : end,
                    "label" : ""})
    return json_graph


### PART 3 : RUN EVERYTHING
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
    
    json_graph = get_json(covered_graph, full_graph, with_omgroups=(not args.ignoretoc), with_text=(not args.notext))
    
    import json
    with open("graph.json", "w") as fp:
        fp.write(json.dumps(json_graph, indent=4))

