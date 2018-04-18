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


def get_file_position(string, offset):
    """ can be used to get linenumber and character offset for a string offset """
    if get_file_position.cached_string == string:
        return get_file_position.cached_positions[offset]
    get_file_position.cached_string = string
    get_file_position.cached_positions = []
    linenumber = 1
    charnumber = 1
    for c in string:
        get_file_position.cached_positions.append((linenumber, charnumber))
        if c == "\n":
            linenumber += 1
            charnumber = 1
        else:
            charnumber += 1
    return get_file_position.cached_positions[offset]
get_file_position.cached_string = ""
get_file_position.cached_positions = []

def get_file_pos_str(string, offset):
    (line, char) = get_file_position(string, offset)
    return f"{line}:{char}"


class StatsGatherer(object):
    """ The stats gatherer gathers all the data and provides some cross-file functionality,
    like checking stuff found in a file against the stuff found in a signature file.
    This design is not ideal and should be reworked. """
    def __init__(self):
        self.defis = []
        self.trefis = []
        self.symis = []
        self.sigfiles = { }
        self.modcounts = {"mhmodnl" : {}, "gviewnl" : {}, "modsig" : {}, "gviewsig" : {}}

        self.mod_name = None
        self.mod_type = None
        self.repo = None
        self.lang = None

        self.file = None
        self.sigfile = None
    
    def set_module(self, name, type_):
        self.mod_name = name
        self.mod_type = type_

        if type_ in ["modsig", "gviewsig"]:
            if name in self.sigfiles[self.repo]:
                self.print_file_message(f"There is already a signature file with name '{name}' in '{self.repo}'")
            else:
                self.sigfiles[self.repo][name] = {
                        "type" : type_,
                        "path" : self.file,
                        }

        self.modcounts[self.mod_type][self.repo] += 1

    def set_repo(self, name):
        self.repo = name
        if self.repo not in self.modcounts["mhmodnl"]:
            for type_ in ["mhmodnl", "modsig", "gviewnl", "gviewsig"]:
                self.modcounts[type_][self.repo] = 0
        if self.repo not in self.sigfiles:
            self.sigfiles[self.repo] = {}

    def set_lang(self, lang):
        self.lang = lang

    def set_file(self, path):
        self.file = path

    def print_file_message(self, message):
        print(f"{self.file}: {message}")

    def push_defi(self, name, string, offset_str):
        assert self.mod_type == "mhmodnl"
        entry = {
                "mod_name" : self.mod_name,
                "repo" : self.repo,
                "lang" : self.lang,
                "name" : name,
                "string" : string,
                "offset" : offset_str,
                "path" : self.file
            }
        if entry in self.defis:
            self.print_file_message(f"Note: Verbalization '{string}' was already introduced for symbol '{name}'")
        self.defis.append(entry)

    def push_symi(self, name, offset_str):
        assert self.mod_type == "modsig"
        entry = {
                "mod_name" : self.mod_name,
                "repo" : self.repo,
                "name" : name,
                "offset" : offset_str,
                "path" : self.file
            }
        if entry in self.symis:
            self.print_file_message(f"Note: Symbol '{name}' was already introduced")
        self.symis.append(entry)

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
TOKEN_BEGIN_MODSIG   = 6
TOKEN_END_MODSIG     = 7
TOKEN_SYM            = 8
TOKEN_BEGIN_GVIEWSIG = 9
TOKEN_END_GVIEWSIG   = 10

re_begin_mhmodnl = re.compile(
        r"\\begin\s*"
        r"\{mhmodnl\}\s*"
        r"(?:\[[^\]]*\])?\s*"                     # optional parameters
        r"\{(?P<name>[\w-]+)\}\s*"                # name
        r"\{(?P<lang>[\w-]+)\}"                   # lang
        )

re_end_mhmodnl = re.compile(
        r"\\end\s*\{mhmodnl\}"
        )

re_arg = r"(?:(?:[^\}\$]+)|(?:\$[^\$]+\$))+"

re_def = re.compile(
        r"\\[Dd]ef(?:i|ii|iii|iv)\s*"
        r"(?:\[(?P<params>[^\]]*)\])?\s*"          # parameters
        r"\{(?P<arg0>" + re_arg + r")\}"           # arg0
        r"(?:\s*\{(?P<arg1>" + re_arg + r")\})?"   # arg1
        r"(?:\s*\{(?P<arg2>" + re_arg + r")\})?"   # arg2
        r"(?:\s*\{(?P<arg3>" + re_arg + r")\})?"   # arg3
        )

re_begin_gviewnl = re.compile(
        r"\\begin\s*"
        r"\{gviewnl\}\s*"
        r"(?:\[[^\]]*\])?\s*"                      # optional parameters
        r"\{(?P<name>[\w-]+)\}\s*"                 # name
        r"\{(?P<lang>[\w-]+)\}"                    # lang
        )

re_end_gviewnl = re.compile(
        r"\\end\s*\{gviewnl\}"
        ) 

re_tref = re.compile(
        r"\\(?:mt|t|Mt|T)ref(?:i|ii|iii|iv)\s*"
        r"(?:\[(?P<params>[^\]]*)\])?\s*"          # parameters
        r"\{(?P<arg0>" + re_arg + r")\}"           # arg0
        r"(?:\s*\{(?P<arg1>" + re_arg + r")\})?"   # arg1
        r"(?:\s*\{(?P<arg2>" + re_arg + r")\})?"   # arg2
        r"(?:\s*\{(?P<arg3>" + re_arg + r")\})?"   # arg3
        )

re_begin_modsig = re.compile(
        r"\\begin\s*"
        r"\{modsig\}\s*"
        r"(?:\[[^\]]*\])?\s*"                     # optional parameters
        r"\{(?P<name>[\w-]+)\}"                   # name
        )

re_end_modsig = re.compile(
        r"\\end\s*\{modsig\}"
        )

re_sym = re.compile(
        r"\\sym(?:i|ii|iii|iv)\s*"
        r"(?:\[(?P<params>[^\]]*)\])?\s*"          # parameters
        r"\{(?P<arg0>" + re_arg + r")\}"           # arg0
        r"(?:\s*\{(?P<arg1>" + re_arg + r")\})?"   # arg1
        r"(?:\s*\{(?P<arg2>" + re_arg + r")\})?"   # arg2
        r"(?:\s*\{(?P<arg3>" + re_arg + r")\})?"   # arg3
        )

re_begin_gviewsig = re.compile(
        r"\\begin\s*"
        r"\{gviewsig\}\s*"
        r"(?:\[[^\]]*\])?\s*"                     # optional parameters
        r"\{(?P<name>[\w-]+)\}"                   # name
        )

re_end_gviewsig = re.compile(
        r"\\end\s*\{gviewsig\}"
        )

regexes = [
        (re_begin_mhmodnl, TOKEN_BEGIN_MHMODNL),
        (re_end_mhmodnl, TOKEN_END_MHMODNL),
        (re_def, TOKEN_DEF),
        (re_begin_gviewnl, TOKEN_BEGIN_GVIEWNL),
        (re_end_gviewnl, TOKEN_END_GVIEWNL),
        (re_tref, TOKEN_TREF),
        (re_begin_modsig, TOKEN_BEGIN_MODSIG),
        (re_end_modsig, TOKEN_END_MODSIG),
        (re_sym, TOKEN_SYM),
        (re_begin_gviewsig, TOKEN_BEGIN_GVIEWSIG),
        (re_end_gviewsig, TOKEN_END_GVIEWSIG),
        ]

def harvest_sig(string, name, gatherer):
    """ harvests the data from signature file content """
    print_unexpected_token = lambda match : gatherer.print_file_message(
            f"Unexpected token at {get_file_pos_str(string, match.start())}: '{match.group(0)}'")
    if name == "all":
        gatherer.print_file_message("Skipping file")
        return
    
    # Check module type
    tokens = parse(string, regexes)
    if len(tokens) == 0:
        raise Exception("No matches - probably an invalid or empty file")

    required_end_sig = None

    for (match, token_type) in tokens:
        if token_type == TOKEN_SYM:
            if required_end_sig == None:
                print_unexpected_token(match)
            args = [match.group(x) for x in ["arg0", "arg1", "arg2", "arg3"]]
            args = [arg for arg in args if arg != None]

            name = "-".join(args)
            gatherer.push_symi(name, get_file_pos_str(string, match.start()))
        elif token_type == TOKEN_BEGIN_MODSIG:
            required_end_sig = TOKEN_END_MODSIG
            gatherer.set_module(name, "modsig")
            if match.group("name") != name:
                gatherer.print_file_message(f"Name '{match.group('name')}' does not match file name")
        elif token_type == TOKEN_BEGIN_GVIEWSIG:
            required_end_sig = TOKEN_END_GVIEWSIG
            gatherer.set_module(name, "gviewsig")
            if match.group("name") != name:
                gatherer.print_file_message(f"Name '{match.group('name')}' does not match file name")
        elif token_type == required_end_sig:
            required_end_sig = None
        else:
            print_unexpected_token(match)

    if required_end_sig:
        gatherer.print_file_message("\\end{gviewsig} or \\end{modsig} missing")



def harvest(string, name, lang, gatherer):
    """ harvests the data from file content """
    print_unexpected_token = lambda match : gatherer.print_file_message(
            f"Unexpected token at {get_file_pos_str(string, match.start())}: '{match.group(0)}'")

    if name == "all":
        gatherer.print_file_message("Skipping file")
        return
    
    # Check module type
    tokens = parse(string, regexes)
    if len(tokens) == 0:
        raise Exception("No matches - probably an invalid or empty file")

    required_end_module = None

    for (match, token_type) in tokens:
        if token_type == TOKEN_DEF:
            if required_end_module == None:
                print_unexpected_token(match)
            params = get_params(match.group("params"))

            args = [match.group(x) for x in ["arg0", "arg1", "arg2", "arg3"]]
            args = [arg for arg in args if arg != None]

            name = params["name"] if "name" in params else "-".join(args)
            val  = " ".join(args)

            gatherer.push_defi(name, val, get_file_pos_str(string, match.start()))
        elif token_type == TOKEN_TREF:
            if required_end_module == None:
                print_unexpected_token(match)
            gatherer.push_trefi()
        elif token_type == TOKEN_BEGIN_MHMODNL:
            required_end_module = TOKEN_END_MHMODNL
            gatherer.set_module(name, "mhmodnl")
            if match.group("name") != name:
                gatherer.print_file_message(f"Name '{match.group('name')}' does not match file name")
            if match.group("lang") != lang:
                gatherer.print_file_message(f"Language '{match.group('lang')}' does not match file name")
        elif token_type == TOKEN_BEGIN_GVIEWNL:
            required_end_module = TOKEN_END_GVIEWNL
            gatherer.set_module(name, "gviewnl")
            if match.group("name") != name:
                gatherer.print_file_message(f"Name '{match.group('name')}' does not match file name")
            if match.group("lang") != lang:
                gatherer.print_file_message(f"Language '{match.group('lang')}' does not match file name")
        elif token_type == required_end_module:
            required_end_module = None
        else:
            print_unexpected_token(match)

    if required_end_module:
        gatherer.print_file_message("\\end{gviewnl} or \\end{mhmodnl} missing")

def preprocess_string(string):
    """ removes comment lines """
    s = re.sub("(^|\n)[\t ]*\%[^\n]*\n", "\\1\n", string)
    while s != string:
        string = s
        s = re.sub("(^|\n)[\t ]*\%[^\n]*\n", "\\1\n", string)
    return string


def gather_stats_for_mod(source_directory, name, gatherer):
    # handle signature file
    path = os.path.join(source_directory, f"{name}.tex")
    gatherer.set_file(path)
    with open(path, "r") as in_file:
        try:
            harvest_sig(preprocess_string(in_file.read()), name, gatherer)
        except Exception as ex:
            gatherer.print_file_message(f"Error while processing file: '{str(ex)}'")

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
                harvest(preprocess_string(in_file.read()), name, lang, gatherer)
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
            if repo == "meta-inf":
                print("Skipping meta-inf")
                continue
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
        print(f"{lang:5}  synsets/symbols: {sc:4}    verbalizations: {dc:4}    symbol references: {tc:4}")
        total_synsets += sc
        total_defis += dc
        total_trefis += tc

    print(f"TOTAL  synsets/symbols: {total_synsets:4}    verbalizations: {total_defis:4}    symbol references: {total_trefis:4}")
    


    print("\n\nSTATISTICS BY REPO")
    synsets = ListCollection()
    trefis = CounterCollection()
    for entry in gatherer.defis:
        synsets.add(entry["repo"], entry["name"])
    for entry in gatherer.trefis:
        trefis.inc(entry["repo"])

    for repo in gatherer.modcounts["mhmodnl"]:
        print(f"{repo:20} modules: {gatherer.modcounts['mhmodnl'][repo]:4}    synsets/symbols: {synsets.unique_count(repo):4}    symbol references: {trefis.get(repo):4}    gviewnls: {gatherer.modcounts['gviewnl'][repo]:3}")



if len(sys.argv) != 2:
    print("Usage:   smglom_stats.py {DIRECTORY}")
    print("Example: smglom_stats.py ~/git/gl_mathhub_info/smglom")
else:
    PRINT_STATS(gather_stats_for_all_repos(sys.argv[1]))
