#!/usr/bin/env python3

# The harvesting functionality should be integrated into `smglom_harvest.py`
# and the rest should be refactored into a separated script based on `smglom_harvest.py`.

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
    def __init__(self, mathhub, repo, doc):
        self.mathhub = mathhub
        self.repo = [repo]
        self.doc = [doc]
        self.inmod = False
        self.files = [(repo, doc)]
        self.file2mod = []
        self.mhinputrefs = []   # mod 2 file

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



TOKEN_MHINPUTREF = 0
TOKEN_BEGIN_OMGROUP = 1
TOKEN_END_OMGROUP = 2


re_arg_core = r"(?:[^\{\}\$]|(?:\$[^\$]+\$)|(\{[^\{\}\$]*\}))+"
re_arg = r"\{(?P<arg>" + re_arg_core + r")\}\s*"
re_param = r"(?:\[(?P<params>[^\]]*)\])?\s*"

re_mhinputref = re.compile(r"\\mhinputref" + re_param + re_arg)
re_begin_omgroup = re.compile(r"\\begin\{omgroup\}" + re_param + re_arg)
re_end_omgroup = re.compile(r"\\end\{omgroup\}")

regexes = [
        (re_mhinputref, TOKEN_MHINPUTREF),
        (re_begin_omgroup, TOKEN_BEGIN_OMGROUP),
        (re_end_omgroup, TOKEN_END_OMGROUP),
        ]

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

def add_omgroup_data(mathhub, root_repo, root_doc, graph):
    # gather data
    context = Context(mathhub, root_repo, root_doc)
    recurse_file(context)

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

def fill_graph(mathhub, root_repo, root_doc, graph):
    potential_modules = add_omgroup_data(mathhub, root_repo, root_doc, graph)
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





def get_json(graph, with_omgroups=True, with_modules=True, with_gimports=True):
    json_graph = {"nodes" : [], "edges" : []}
    omgr2id = lambda omgr : omgr[0] + "?" + omgr[1]

    if with_omgroups:
        for node in graph.omgroup_nodes.keys():
            json_graph["nodes"].append({
                "id" : omgr2id(node),
                "style" : "theory",
                "label" : graph.omgroup_nodes[node]["label"] })
        for start,end in graph.omgroup_edges:
            json_graph["edges"].append({
                "id" : omgr2id(start) + "??" + omgr2id(end),
                "style" : "include",
                "from" : omgr2id(start),
                "to" : omgr2id(end),
                "label" : ""})
    if with_omgroups and with_modules:
        for start,end in graph.omgroup2module_edges:
            if end in graph.module_nodes:
                json_graph["edges"].append({
                    "id" : omgr2id(start) + "??" + end,
                    "style" : "include",
                    "from" : omgr2id(start),
                    "to" : end,
                    "label" : ""})

    if with_modules:
        for node in graph.module_nodes:
            json_graph["nodes"].append({
                    "id" : node,
                    "style" : "model",
                    "label" : graph.module_nodes[node]["label"]})
        for start,end in graph.module_edges:
            assert start in graph.module_nodes
            assert end in graph.module_nodes
            json_graph["edges"].append({
                "id" : start + "??" + end,
                "style" : "include",
                "from" : start,
                "to" : end,
                "label" : ""})

    if with_gimports:
        for node in graph.g_nodes.keys():
            json_graph["nodes"].append({
                "id" : node,
                "style" : "model",
                "label" : graph.g_nodes[node]["label"]})
        for start,end in graph.g_edges.keys():
            assert start in graph.module_nodes.keys() or start in graph.g_nodes.keys()
            if end in graph.module_nodes.keys() or end in graph.g_nodes.keys():
                json_graph["edges"].append({
                    "id" : start + "??" + end,
                    "style" : "modelinclude",
                    "from" : start,
                    "to" : end,
                    "label" : ""})
    return json_graph

### PART 3 : RUN EVERYTHING

mathhub = os.path.abspath(sys.argv[1])
root_repo = sys.argv[2]
root_doc = sys.argv[3]

print("Mathhub: " + mathhub)
print("root repo: " + root_repo)
print("root doc: " + root_doc)

graph = Graph()

fill_graph(mathhub, root_repo, root_doc, graph)

json_graph = get_json(graph)

import json
with open("graph.json", "w") as fp:
    fp.write(json.dumps(json_graph, indent=4))

