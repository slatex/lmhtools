#!/usr/local/bin/python3

"""
Creates statistics tex glossary files.

For printing different statistics, feel free to change PRINT_STATS.
"""

import re
import sys
import os


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

def get_params(param_str):
    if param_str == None:
        return { }

    return {
            e[0] : "=".join(e[1:])
                for e in [p.split("=") for p in param_str.split(",") if "=" in p]
        }



class StatsGatherer(object):
    def __init__(self):
        self.defis = []
        self.trefis = []
        self.modcounts = {"mhmodnl" : {}, "gviewnl" : {}}

        self.mod_name = None
        self.mod_type = None
        self.repo = None
        self.lang = None

        self.file = None
    
    def set_module(self, name, type_):
        self.mod_name = name
        self.mod_type = type_
        self.modcounts[self.mod_type][self.repo] += 1

    def set_repo(self, name):
        self.repo = name
        if self.repo not in self.modcounts["mhmodnl"]:
            self.modcounts["mhmodnl"][self.repo] = 0
            self.modcounts["gviewnl"][self.repo] = 0

    def set_lang(self, lang):
        self.lang = lang

    def set_file(self, path):
        self.file = path

    def print_file_message(self, message):
        print(f"{self.file}: {message}")

    def push_defi(self, name, string):
        assert self.mod_type == "mhmodnl"
        self.defis.append(
            {
                "mod_name" : self.mod_name,
                "repo" : self.repo,
                "lang" : self.lang,
                "name" : name,
                "string" : string
            }
        )

    def push_trefi(self):
        self.trefis.append(
            {
                "mod_name" : self.mod_name,
                "mod_type" : self.mod_type,
                "repo" : self.repo,
                "lang" : self.lang
            }
        )

TOKEN_BEGIN_MHMODNL  = 0
TOKEN_END_MHMODNL    = 1
TOKEN_DEF            = 2
TOKEN_BEGIN_GVIEWNL  = 3
TOKEN_END_GVIEWNL    = 4
TOKEN_TREF           = 5

re_begin_mhmodnl = re.compile(
        r"\\begin\s*"
        r"\{mhmodnl\}\s*"
        r"(?:\[[^\]]*\])?\s*"            # optional parameters
        r"\{(?P<name>[\w-]+)\}\s*"       # name
        r"\{(?P<lang>[\w-]+)\}"          # lang
        )

re_end_mhmodnl = re.compile(
        r"\\end\s*\{mhmodnl\}"
        )

re_def = re.compile(
        r"\\def(?:i|ii|iii|iv)\s*"
        r"(?:\[(?P<params>[^\]]*)\])?\s*" # parameters
        r"\{(?P<arg0>[^\}]+)\}"           # arg0
        r"(?:\s*\{(?P<arg1>[^\}]+)\})?"   # arg1
        r"(?:\s*\{(?P<arg2>[^\}]+)\})?"   # arg2
        r"(?:\s*\{(?P<arg3>[^\}]+)\})?"   # arg3
        )

re_begin_gviewnl = re.compile(
        r"\\begin\s*"
        r"\{gviewnl\}\s*"
        r"(?:\[[^\]]*\])?\s*"            # optional parameters
        r"\{(?P<name>[\w-]+)\}\s*"       # name
        r"\{(?P<lang>[\w-]+)\}"          # lang
        )

re_end_gviewnl = re.compile(
        r"\\end\s*\{gviewnl\}"
        ) 

# the tref* regex NEEDS CLARIFICATION! (mtref* etc?)
re_tref = re.compile(
        r"\\m?tref(?:i|ii|iii|iv)\s*"
        r"(?:\[(?P<params>[^\]]*)\])?\s*" # parameters
        r"\{(?P<arg0>[^\}]+)\}"           # arg0
        r"(?:\s*\{(?P<arg1>[^\}]+)\})?"   # arg1
        r"(?:\s*\{(?P<arg2>[^\}]+)\})?"   # arg2
        r"(?:\s*\{(?P<arg3>[^\}]+)\})?"   # arg3
        )

regexes = [
        (re_begin_mhmodnl, TOKEN_BEGIN_MHMODNL),
        (re_end_mhmodnl, TOKEN_END_MHMODNL),
        (re_def, TOKEN_DEF),
        (re_begin_gviewnl, TOKEN_BEGIN_GVIEWNL),
        (re_end_gviewnl, TOKEN_END_GVIEWNL),
        (re_tref, TOKEN_TREF)
        ]


def harvest(string, name, gatherer):
    """ harvests the data from file content """
    
    # Check module type
    tokens = parse(string, regexes)
    if len(tokens) == 0:
        raise Exception("No matches - probably an invalid or empty file")

    required_end_module = None

    for (match, token_type) in tokens:
        if token_type == TOKEN_DEF:
            if required_end_module == None:
                gatherer.print_file_message(f"Unexpected token type: {token_type}")
            params = get_params(match.group("params"))

            args = [match.group(x) for x in ["arg0", "arg1", "arg2", "arg3"]]
            args = [arg for arg in args if arg != None]

            name = params["name"] if "name" in params else "-".join(args)
            val  = " ".join(args)

            gatherer.push_defi(name, val)
        elif token_type == TOKEN_TREF:
            if required_end_module == None:
                gatherer.print_file_message(f"Unexpected token type: {token_type}")
            gatherer.push_trefi()
        elif token_type == TOKEN_BEGIN_MHMODNL:
            required_end_module = TOKEN_END_MHMODNL
            gatherer.set_module(name, "mhmodnl")
            if match.group("name") != name:
                gatherer.print_file_message("Name does not match file name")
        elif token_type == TOKEN_BEGIN_GVIEWNL:
            required_end_module = TOKEN_END_GVIEWNL
            gatherer.set_module(name, "gviewnl")
            if match.group("name") != name:
                gatherer.print_file_message("Name does not match file name")
        elif token_type == required_end_module:
            required_end_module = None
        else:
            gatherer.print_file_message(f"Unexpected token type: {token_type}")

    if required_end_module:
        gatherer.print_file_message("\\end{gviewnl} or \\end{mhmodnl} missing")


def gather_stats_for_mod(source_directory, name, gatherer):
    # determine languages
    regex = re.compile(name + r"\.(?P<lang>[a-zA-Z]+)\.tex")
    langs = []
    for file_name in os.listdir(source_directory):
        m = regex.match(file_name)
        if m != None:
            langs.append(m.group("lang"))

    for lang in langs:
        # harvest data
        path = os.path.join(source_directory, f"{name}.{lang}.tex")
        gatherer.set_file(path)
        gatherer.set_lang(lang)
        with open(path, "r") as in_file:
            try:
                harvest(in_file.read(), name, gatherer)
            except Exception as ex:
                gatherer.print_file_message(f"Error while processing file: '{str(ex)}'")
                continue

def gather_stats_for_repo(repo_directory, gatherer):
    regex = re.compile(r"(?P<name>[a-zA-Z0-9-]+)\.tex")
    full_path = os.path.join(repo_directory, "source")
    for file_name in os.listdir(full_path):
        m = regex.match(file_name)
        if m != None:
            gather_stats_for_mod(full_path, m.group("name"), gatherer)

def gather_stats_for_all_repos(directory):
    gatherer = StatsGatherer()
    for repo in os.listdir(directory):
        try:
            gatherer.set_repo(repo)
            gather_stats_for_repo(os.path.join(directory, repo), gatherer)
        except Exception as ex:
            print("Error while obtaining statistics for repo " + os.path.join(directory, repo) + ":")
            print(ex)
            continue
    return gatherer



def PRINT_STATS(gatherer):
    """ Modify this for your needs"""

    class CounterCollection(object):
        def __init__(self):
            self.counters = {}

        def inc(self, name):
            if name not in self.counters:
                self.counters[name] = 0
            self.counters[name] += 1

        def get(self, name):
            if name in self.counters:
                return self.counters[name]
            else:
                return 0

    class ListCollection(object):
        def __init__(self):
            self.lists = {}

        def add(self, name, entry):
            if name not in self.lists:
                self.lists[name] = []
            self.lists[name].append(entry)

        def unique_count(self, name):
            if name in self.lists:
                return len(set(self.lists[name]))
            else:
                return 0

    print("STATISTICS BY LANGUAGE")
    synsets = ListCollection()
    defis = ListCollection()
    trefis = CounterCollection()
    for entry in gatherer.defis:
        synsets.add(entry["lang"], entry["name"])
        defis.add(entry["lang"], entry["name"] + "|" + entry["string"])
    for entry in gatherer.trefis:
        trefis.inc(entry["lang"])
    total_synsets = 0
    total_defis = 0
    total_trefis = 0
    for lang in synsets.lists:
        dc = defis.unique_count(lang)
        sc = synsets.unique_count(lang)
        tc = trefis.counters[lang]
        print(f"{lang:5}  defis: {dc:4}    synsets: {sc:4}    trefis: {tc:4}")
        total_synsets += sc
        total_defis += dc
        total_trefis += tc

    print(f"TOTAL  defis: {total_defis:4}    synsets: {total_synsets:4}    trefis: {total_trefis:4}")
    


    print("\n\nSTATISTICS BY REPO")
    synsets = ListCollection()
    trefis = CounterCollection()
    for entry in gatherer.defis:
        synsets.add(entry["repo"], entry["name"])
    for entry in gatherer.trefis:
        trefis.inc(entry["repo"])

    for repo in gatherer.modcounts["mhmodnl"]:
        print(f"{repo:20} synsets: {synsets.unique_count(repo):4}    trefis: {trefis.get(repo):4}    mhmodnls: {gatherer.modcounts['mhmodnl'][repo]:4}    gviewnls: {gatherer.modcounts['gviewnl'][repo]:3}")



if len(sys.argv) != 2:
    print("Usage:   smglom_stats.py {DIRECTORY}")
    print("Example: smglom_stats.py ~/git/gl_mathhub_info/smglom")
else:
    PRINT_STATS(gather_stats_for_all_repos(sys.argv[1]))
