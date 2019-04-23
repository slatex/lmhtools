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




mathhub = sys.argv[1]
root_repo = sys.argv[2]
root_doc = sys.argv[3]

print("Mathhub: " + mathhub)
print("root repo: " + root_repo)
print("root doc: " + root_doc)

context = Context(mathhub, root_repo, root_doc)
recurse_file(context)

# print(context.file2mod)
# print(context.mhinputrefs)


print("Done gathering")

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


blocked_nodes = []
potential_modules = []
for v in omgroup2files.values():
    for e in v:
        if e not in file2omgroups:
            e2 = os.path.join(mathhub, e[0], "source", e[1]) + ".tex"
            potential_modules.append(e2)
            blocked_nodes.append(e2)


### PART 2 : PARSING MODULES

gatherer = harvest.DataGatherer()
logger = harvest.SimpleLogger(2)
potential_nodes = []
potential_edges = []
while potential_modules:
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
        if node not in potential_nodes:
            potential_nodes.append(node)

    potential_modules = []
    for imp in gatherer.importmhmodules:
        destnode = imp["dest_path"]
        if destnode not in blocked_nodes:
            blocked_nodes.append(destnode)
            potential_modules.append(destnode)
        potential_edges.append((imp["path"], destnode))



### PART 3 : GRAPH GENERATION

graph = {"nodes" : [], "edges" : []}


for omgroup in omgroup2files.keys():
    graph["nodes"].append({
            "id" : "?".join([omgroup[0],omgroup[1],str(omgroup[2])]),
            "style" : "theory",
            "label" : omgroup[3],
            "url" : "None" })
    for f in omgroup2files[omgroup]:
        if f in file2omgroups:
            for omg2 in file2omgroups[f]:
                graph["edges"].append({
                    "id" : "?".join([omgroup[0],omgroup[1],str(omgroup[2]),omg2[0],omg2[1],str(omg2[2])]),
                    "style" : "view",
                    "from" : "?".join([omgroup[0],omgroup[1],str(omgroup[2])]),
                    "to" : "?".join([omg2[0], omg2[1], str(omg2[2])]),
                    "label" : "mhincluderef",
                    "url" : "None" })
        else:
            path = os.path.join(mathhub, f[0], "source", f[1]) + ".tex"
            node = path
            if node in potential_nodes:
                graph["edges"].append({
                    "id" : "?".join([omgroup[0],omgroup[1],node[0],node[1]]),
                    "style" : "include",
                    "from" : "?".join([omgroup[0],omgroup[1],str(omgroup[2])]),
                    "to" : node,
                    "label" : "mhincluderef",
                    "url" : "None" })
            

for node in potential_nodes:
    graph["nodes"].append({
            "id" : node,
            "style" : "model",
            "label" : os.path.split(node)[1],
            "url" : "None"
        })

for start, end in potential_edges:
    if end in potential_nodes:
        graph["edges"].append({
                "id" : start + "?" + end,
                "style" : "view",
                "from" : start,
                "to" : end,
                "label" : "usemhmodule",
                "url" : "None" })

import json
print(json.dumps(graph, indent=4))
