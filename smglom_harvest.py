#!/usr/bin/env python3

"""
Can be used to harvest data from smglom.

In particular, data is gathered about introduced symbols, their verbalizations,
trefis, as well as about the nl and signature files.

It is used in smglom_stats.py and smglom_debug.py, but it can also be run as
a stand-alone script, writing the collected data to stdout.
Note that the LaTeX is not parsed properly - instead, regular expressions are
used, which come with their natural limitiations.
"""

import os
import re
import traceback

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
    """ returns dictionary of comma-separated key=value pairs """
    if param_str == None:
        return { }

    return {
            param.group("key") : param.group("val")
                for param in re.finditer(get_params.re_param, param_str)
        }

get_params.re_param = re.compile(
        r"(?P<key>[a-zA-Z0-9_-]+)"
        r"(?:=(?P<val>(?:[^\{\},]+)|(?:\{[^\{\}]+\})))?")


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

def preprocess_string(string):
    """ removes comment lines, but keeps linebreaks to maintain line numbers
        TODO: Implement this in a cleaner way!
    """
    s = re.sub("(^|\n)[\t ]*\%[^\n]*\n", "\\1\n", string)
    while s != string:
        string = s
        s = re.sub("(^|\n)[\t ]*\%[^\n]*\n", "\\1\n", string)
    return string

def exception_to_string(excp):
    """ from stackoverflow """
    stack = traceback.extract_stack()[:-3] + traceback.extract_tb(excp.__traceback__)  # add limit=??
    pretty = traceback.format_list(stack)
    return ''.join(pretty) + '\n  {} {}'.format(excp.__class__,excp)


class SimpleLogger(object):
    def __init__(self, verbosity):
        assert 0 <= verbosity <= 4
        self.verbosity = verbosity

    def format_filepos(self, path, offset=None, with_col=False):
        return (path + " at " + offset if offset else path) + (":" if with_col else "")

    def log(self, message, minverbosity=1, filepath=None, offset=None):
        if self.verbosity < minverbosity:
            return False
        
        if filepath:
            print(f"{self.format_filepos(filepath, offset, True)} {message}\n")
        else:
            print(f"{message}")

        return True


class HarvestContext(object):
    """ The HarvestContext keeps (among other things) data about 'what' is currently processed.
        This includes things like the current repository, file name, ...
        It also has a reference to the DataGatherer. """
    def __init__(self, logger, gatherer):

        self.logger = logger
        self.gatherer = gatherer

        self.mod_name = None
        self.mod_type = None
        self.repo = None
        self.lang = None
        self.file = None

        self.something_was_logged = False

    def log(self, message, minverbosity=1, offsetstr=None, forfile = True):
        was_logged = self.logger.log(message, minverbosity,
                        filepath=self.file if forfile else None,
                        offset=offsetstr)
        self.something_was_logged = self.something_was_logged or was_logged

class DataGatherer(object):
    """ The DataGatherer collects all the data from the files """
    def __init__(self):
        self.defis = []
        self.trefis = []
        self.symis = []
        self.sigfiles = []
        self.langfiles = []
        self.modules = []
        self.repos = []

    def push_repo(self, namespace, ctx):
        self.repos.append({
            "repo" : ctx.repo,
            "namespace" : namespace,
        })

    def push_sigfile(self, align, ctx):
        assert ctx.mod_type in ["modsig", "gviewsig"]
        self.sigfiles.append({
            "type" : ctx.mod_type,
            "path" : ctx.file,
            "repo" : ctx.repo,
            "align" : align,
            "mod_name" : ctx.mod_name,
        })

    def push_module(self, ctx):
        assert ctx.mod_type == "module"
        self.modules.append({
            "path" : ctx.file,
            "repo" : ctx.repo,
            "mod_name" : ctx.mod_name,
        })

    def push_langfile(self, ctx):
        assert ctx.mod_type in ["mhmodnl", "gviewnl"]
        self.langfiles.append({
            "type" : ctx.mod_type,
            "path" : ctx.file,
            "repo" : ctx.repo,
            "mod_name" : ctx.mod_name,
            "lang" : ctx.lang,
        })

    def push_defi(self, name, string, offset_str, ctx, params):
        assert ctx.mod_type in ["mhmodnl", "module"]
        entry = {
                "mod_name" : ctx.mod_name,
                "repo" : ctx.repo,
                "lang" : ctx.lang,
                "name" : name,
                "string" : string,
                "offset" : offset_str,
                "path" : ctx.file,
                "params" : params,
            }
        self.defis.append(entry)

    def push_symi(self, name, offset_str, type_, noverb, align, ctx, params, implicit=False):
        assert ctx.mod_type in ["modsig", "module"]
        assert type_ in ["symi", "symdef"]
        entry = {
                "mod_name" : ctx.mod_name,
                "repo" : ctx.repo,
                "name" : name,
                "offset" : offset_str,
                "path" : ctx.file,
                "type" : type_,
                "noverb" : noverb,
                "align" : align,
                "params" : params,
                "implicit" : implicit,
            }
        self.symis.append(entry)

    def push_trefi(self, offset_str, ctx):
        self.trefis.append(
            {
                "mod_name" : ctx.mod_name,
                "mod_type" : ctx.mod_type,
                "repo" : ctx.repo,
                "offset" : offset_str,
                "lang" : ctx.lang,
                "path" : ctx.file,
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
TOKEN_SYMDEF         = 11
TOKEN_BEGIN_MODULE   = 12
TOKEN_END_MODULE     = 13

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

re_arg = r"(?:[^\{\}\$]|(?:\$[^\$]+\$)|(\{[^\{\}\$]*\}))+"

re_def = re.compile(
        r"\\(?P<start>d|D|ad)ef(?P<arity>i|ii|iii|iv)s?\s*"
        r"(?:\[(?P<params>[^\]]*)\])?\s*"          # parameters
        r"\{(?P<arg0>" + re_arg + r")\}"           # arg0
        r"(?:\s*\{(?P<arg1>" + re_arg + r")\})?"   # arg1
        r"(?:\s*\{(?P<arg2>" + re_arg + r")\})?"   # arg2
        r"(?:\s*\{(?P<arg3>" + re_arg + r")\})?"   # arg3
        r"(?:\s*\{(?P<arg4>" + re_arg + r")\})?"   # arg4 (for adefi*s)
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
        r"\\(?P<start>at|mt|t|Mt|T)ref(?P<arity>i|ii|iii|iv)s?\s*"
        r"(?:\[(?P<params>[^\]]*)\])?\s*"          # parameters
        r"\{(?P<arg0>" + re_arg + r")\}"           # arg0
        r"(?:\s*\{(?P<arg1>" + re_arg + r")\})?"   # arg1
        r"(?:\s*\{(?P<arg2>" + re_arg + r")\})?"   # arg2
        r"(?:\s*\{(?P<arg3>" + re_arg + r")\})?"   # arg3
        r"(?:\s*\{(?P<arg4>" + re_arg + r")\})?"   # arg4
        )

re_begin_modsig = re.compile(
        r"\\begin\s*"
        r"\{modsig\}\s*"
        r"(?:\[(?P<params>[^\]]*)\])?\s*"         # parameters
        r"\{(?P<name>[\w-]+)\}"                   # name
        )

re_end_modsig = re.compile(
        r"\\end\s*\{modsig\}"
        )

re_sym = re.compile(
        r"\\sym(?P<arity>i|ii|iii|iv)\*?\s*"
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

re_symdef = re.compile(
        r"\\symdef\s*"
        r"(?:\[(?P<params>[^\]]*)\])?\s*"          # parameters
        r"\{(?P<arg0>" + re_arg + r")\}"           # arg0
        )

re_namespace = re.compile(
        r"\\namespace\s*"
        r"(?:\[(?P<params>[^\]]*)\])?\s*"          # parameters
        r"\{(?P<arg>" + re_arg + r")\}"            # arg
        )

re_begin_module = re.compile(
        r"\\begin\s*"
        r"\{module\}\s*"
        r"(?:\[(?P<params>[^\]]*)\])?\s*"          # parameters
        )

re_end_module = re.compile(
        r"\\end\s*\{module\}"
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
        (re_symdef, TOKEN_SYMDEF),
        (re_begin_module, TOKEN_BEGIN_MODULE),
        (re_end_module, TOKEN_END_MODULE),
        ]

def get_noverb(param_dict):
    if "noverb" not in param_dict:
        return []
    val = param_dict["noverb"]
    if val == None:
        return "all"
    if val == "all":
        return "all"
    if val[0] == "{" and val[-1] == "}":
        return val[1:-1].split(",")
    return [val]

def get_align(params, name):
    if "align" in params:
        if params["align"] != None:
            return params["align"]
        return name
    elif "noalign" in params:
        return "noalign"
    else:
        return None

def get_args(match, is_symi, string, ctx):
    """ Highly specialized code - only use with great caution! """
    possible_args = ["arg0", "arg1", "arg2", "arg3"]
    if not is_symi:
        possible_args.append("arg4")

    args = [match.group(x) for x in possible_args]
    args = [arg for arg in args if arg != None]
    one_plus = ""
    if not is_symi and match.group("start").startswith("a"):        # adefi etc.
        one_plus = "1+"
        args = args[1:]

    arity = {"i" : 1, "ii" : 2, "iii" : 3, "iv" : 4}[match.group("arity")]
    if len(args) != arity:
        ctx.log(f"Arity mismatch (needs {one_plus}{arity} arguments, but found {one_plus}{len(args)}): '{match.group(0)}'",
                2, get_file_pos_str(string, match.start()))
    return args

def harvest_sig(string, name, ctx):
    """ harvests the data from signature file content """
    tokens = parse(string, regexes)
    if len(tokens) == 0:
        ctx.log("No matches found in file", 3)
        return
    
    required_end_sig = None
    isacceptablefile = False
    mod_align = None

    for (match, token_type) in tokens:
        if token_type == TOKEN_SYM:
            if required_end_sig == None:
                ctx.log(f"Require \\begin{modsig} or \\begin{gviewsig} before token: '{match.group(0)}'",
                        1, get_file_pos_str(string, match.start()))
                continue

            args = get_args(match, True, string, ctx) 
            tname = "-".join(args)
            params = get_params(match.group("params"))
            ctx.gatherer.push_symi(tname, get_file_pos_str(string, match.start()), "symi", get_noverb(params), get_align(params, tname), ctx, params)
        elif token_type == TOKEN_SYMDEF:
            if required_end_sig == None:
                ctx.log("Require \\begin{modsig} or \\begin{gviewsig} before token: " + f"'{match.group(0)}'",
                        1, get_file_pos_str(string, match.start()))
                continue
            params = get_params(match.group("params"))
            arg = match.group("arg0")
            tname = params["name"] if "name" in params else arg
            ctx.gatherer.push_symi(tname, get_file_pos_str(string, match.start()), "symdef", get_noverb(params), get_align(params, tname), ctx, params)
        elif token_type == TOKEN_BEGIN_MODSIG:
            isacceptablefile = True
            required_end_sig = TOKEN_END_MODSIG
            if match.group("name") != name:
                ctx.log(f"Name '{match.group('name')}' does not match file name",
                        2, get_file_pos_str(string, match.start()))
            ctx.mod_type = "modsig"
            ctx.mod_name = match.group("name")
            params = get_params(match.group("params"))
            mod_align = get_align(params, ctx.mod_name)
        elif token_type == TOKEN_BEGIN_GVIEWSIG:
            isacceptablefile = True
            required_end_sig = TOKEN_END_GVIEWSIG
            if match.group("name") != name:
                ctx.log(f"Name '{match.group('name')}' does not match file name",
                        2, get_file_pos_str(string, match.start()))
            ctx.mod_type = "gviewsig"
            ctx.mod_name = match.group("name")
        elif token_type == required_end_sig:
            required_end_sig = None
        else:
            ctx.log(f"Unexpected token: '{match.group(0)}'", 2, get_file_pos_str(string, match.start()))

    if required_end_sig:
        ctx.log("\\end{gviewsig} or \\end{modsig} missing", 1)
        return
    if not isacceptablefile:
        ctx.log("File didn't have \\begin{modsig} or \\begin{gviewsig}", 1)
        return
    ctx.gatherer.push_sigfile(mod_align, ctx)



def harvest_nl(string, name, lang, ctx):
    """ harvests the data from file content """
    tokens = parse(string, regexes)
    if len(tokens) == 0:
        ctx.log("No matches found in file", 3)
        return

    required_end_module = None
    isacceptablefile = False

    for (match, token_type) in tokens:
        if token_type == TOKEN_DEF:
            if required_end_module == None or required_end_module == TOKEN_END_GVIEWNL:
                ctx.log(f"Require \\begin{mhmodnl} before token: '{match.group(0)}'",
                        1, get_file_pos_str(string, match.start()))
                continue
            params = get_params(match.group("params"))

            args = get_args(match, False, string, ctx)

            tname = params["name"] if "name" in params else "-".join(args)
            val  = " ".join(args)

            ctx.gatherer.push_defi(tname, val, get_file_pos_str(string, match.start()), ctx, params)
        elif token_type == TOKEN_TREF:
            if required_end_module == None:
                ctx.log(f"Require \\begin{mhmodnl} or \\begin{gviewnl} before token: '{match.group(0)}'",
                        1, get_file_pos_str(string, match.start()))
                continue
            get_args(match, False, string, ctx)    # print error messages for arity violations
            ctx.gatherer.push_trefi(get_file_pos_str(string, match.start()), ctx)
        elif token_type == TOKEN_BEGIN_MHMODNL:
            isacceptablefile = True
            required_end_module = TOKEN_END_MHMODNL
            if match.group("name") != name:
                ctx.log(f"Name '{match.group('name')}' does not match file name", 1, get_file_pos_str(string, match.start()))
            if match.group("lang") != lang:
                ctx.log(f"Language '{match.group('lang')}' does not match file name", 1, get_file_pos_str(string, match.start()))
            ctx.lang = match.group("lang")
            ctx.mod_name = match.group("name")
            ctx.mod_type = "mhmodnl"
        elif token_type == TOKEN_BEGIN_GVIEWNL:
            isacceptablefile = True
            required_end_module = TOKEN_END_GVIEWNL
            if match.group("name") != name:
                ctx.log(f"Name '{match.group('name')}' does not match file name", 1, get_file_pos_str(string, match.start()))
            if match.group("lang") != lang:
                ctx.log(f"Language '{match.group('lang')}' does not match file name", 1, get_file_pos_str(string, match.start()))
            ctx.lang = match.group("lang")
            ctx.mod_name = match.group("name")
            ctx.mod_type = "gviewnl"
        elif token_type == required_end_module:
            required_end_module = None
        else:
            ctx.log(f"Unexpected token: '{match.group(0)}'", 2, get_file_pos_str(string, match.start()))

    if required_end_module:
        ctx.log("\\end{gviewnl} or \\end{mhmodnl} missing", 1)
        return

    if not isacceptablefile:
        ctx.log("File didn't have \\begin{mhmodnl} or \\begin{gviewnl}", 1)
        return

    ctx.gatherer.push_langfile(ctx)

def harvest_mono(string, ctx):
    """ harvests the data from file content """

    # Check module type
    tokens = parse(string, regexes)
    if len(tokens) == 0:
        ctx.log("No matches found in file", 2)
        return

    in_module = False
    in_named_module = False

    for (match, token_type) in tokens:
        if token_type == TOKEN_DEF:
            if not in_named_module:
                ctx.log("Require \\begin{module}[id=...] before token: '" + match.group(0) + "'",
                        1, get_file_pos_str(string, match.start()))
                continue
            params = get_params(match.group("params"))

            args = get_args(match, False, string, ctx)

            name = params["name"] if "name" in params else "-".join(args)
            val  = " ".join(args)

            ctx.gatherer.push_defi(name, val, get_file_pos_str(string, match.start()), ctx, params)
            ctx.gatherer.push_symi(name, get_file_pos_str(string, match.start()), "symi", get_noverb(params), get_align(params, name), ctx, params, implicit=True)
        elif token_type == TOKEN_TREF:
            if not in_module:
                ctx.log("Require \\begin{module} before token: '" + match.group(0) + "'",
                        1, get_file_pos_str(string, match.start()))
                continue
            get_args(match, False, string, ctx)    # print error messages for arity violations
            ctx.gatherer.push_trefi(get_file_pos_str(string, match.start()), ctx)
        elif token_type == TOKEN_BEGIN_MODULE:
            if in_module:
                ctx.log("Nested modules are not supported",
                        1, get_file_pos_str(string, match.start()))
            in_module = True
            ctx.lang = "?"
            params = get_params(match.group("params"))
            if "id" in params:
                ctx.mod_name = params["id"]
                in_named_module = True
            else:
                ctx.mod_name = "?"
                in_named_module = False
            ctx.mod_type = "module"
        elif token_type == TOKEN_END_MODULE:
            if in_named_module:
                ctx.gatherer.push_module(ctx)
            in_module = False
            in_named_module = False
        else:
            if token_type == TOKEN_SYMDEF and in_named_module:
                continue
            ctx.log(f"Unexpected token: '{match.group(0)}'", 2, get_file_pos_str(string, match.start()))

    if in_module:
        ctx.log("\\end{module} missing", 1)
        return

def harvest_trefi(string, ctx):
    """ harvests the trefis from unidentified file content """

    # Check module type
    tokens = parse(string, regexes)
    ctx.mod_name = "?"
    ctx.mod_type = "?"

    for (match, token_type) in tokens:
        if token_type == TOKEN_TREF:
            #ctx.log("Warning: Found trefi token in unidentified file",
            #        3, get_file_pos_str(string, match.start()))
            get_args(match, False, string, ctx)    # print error messages for arity violations
            ctx.gatherer.push_trefi(get_file_pos_str(string, match.start()), ctx)
        else:
            ctx.log(f"Unexpected token in unidentified file: '{match.group(0)}'", 2, get_file_pos_str(string, match.start()))
    

def identify_file(content):
    match = identify_file.regex.search(content)
    if not match:
        return None
    mod = match.group("mod")
    if mod == "module":
        return "mono"
    elif mod in ["modsig", "gviewsig"]:
        return "sig"
    assert mod in ["mhmodnl", "gviewnl"]
    return "nl"

identify_file.regex = re.compile(r"\\begin\s*\{(?P<mod>(module)|(modsig)|(mhmodnl)|(gviewnl)|(gviewsig))\}")

def harvest_repo_metadata(repo_directory, ctx):
    preamble_path = os.path.join(repo_directory, "lib", "preamble.tex")
    namespace = ""
    if os.path.isfile(preamble_path):
        with open(preamble_path, "r") as fp:
            content = fp.read()
            match = re_namespace.search(content)
            if match:
                namespace = match.group("arg")
    ctx.gatherer.push_repo(namespace, ctx)

def gather_data_for_repo(repo_directory, ctx):
    harvest_repo_metadata(repo_directory, ctx)
    dir_path = os.path.join(repo_directory, "source")
    for root, dirs, files in os.walk(dir_path):
        for file_name in files:
            m = gather_data_for_repo.file_regex.match(file_name)
            if m == None:
                continue
            name = m.group("name")
            lang = m.group("lang")
            file_path = os.path.join(root, f"{name}.{lang}.tex" if lang else f"{name}.tex")
            if name in ["all", "localpaths"]:
                continue

            with open(file_path, "r") as fp:
                ctx.file = file_path
                try:
                    string = preprocess_string(fp.read())
                    file_type = identify_file(string)
                    if not file_type:
                        harvest_trefi(string, ctx)
                        continue
                    if lang:
                        if file_type != "nl":
                            ctx.log("Doesn't appear to be a language file - skipping it", 2)
                            continue
                        harvest_nl(string, name, lang, ctx)
                    elif file_type == "sig":
                        harvest_sig(string, name, ctx)
                    elif file_type == "mono":
                        harvest_mono(string, ctx)
                    else:
                        assert file_type == "nl" and not lang
                        ctx.log("It appears to be a language file, but the filename doesn't indicate that", 2)
                except Exception as ex:
                    ctx.log(f"An internal error occured during processing:\n'{exception_to_string(ex)}'", 0)
                    continue


gather_data_for_repo.file_regex = re.compile(r"^(?P<name>[a-zA-Z0-9-]+)(\.(?P<lang>[a-zA-Z]+))?\.tex$")

def gather_data_for_all_repos(directory, ctx):
    """ recursively finds git repos and calls gather_data_for_all_repos on them """
    if os.path.isdir(os.path.join(directory, ".git")):  ## TODO: Is there a better way?
        try:
            ctx.repo = directory.split("/")[-1]   ## TODO: Do this system-independently
            gather_data_for_repo(directory, ctx)
        except Exception as ex:
            ctx.log("Error while obtaining statistics for repo " + os.path.join(directory, repo) + ":\n" + exception_to_string(ex), forfile=False)
        return

    for subdir in os.listdir(directory):
        if subdir == "meta-inf":
            # if ctx.verbosity >= 4:
            #     print("Skipping meta-inf")
            continue
        subdirpath = os.path.join(directory, subdir)
        if os.path.isdir(subdirpath):
            gather_data_for_all_repos(subdirpath, ctx)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Script for gathering SMGloM data",
            epilog="Example call: smglom_harvest.py -v1 defi ../..")
    parser.add_argument("-v", "--verbosity", type=int, default=1, choices=range(4),
            help="the verbosity (default: 1)")
    parser.add_argument("COMMAND", choices=["repo", "defi", "trefi", "symi", "sigfile", "langfile"],
            help="print this type of data")
    parser.add_argument("DIRECTORY", nargs="+",
            help="git repo or higher level directory from which data is gathered")
    args = parser.parse_args()

    verbosity = args.verbosity
    if verbosity >= 2:
        print("GATHERING DATA\n")
    ctx = HarvestContext(SimpleLogger(verbosity), DataGatherer())
    for directory in args.DIRECTORY:
        gather_data_for_all_repos(directory, ctx)

    if verbosity >= 2 or ctx.something_was_logged:
        print("\n\nRESULTS\n")

    command = args.COMMAND
    if command == "repo":
        for repo in ctx.gatherer.repos:
            print(f"{repo['repo']} namespace={repr(repo['namespace'])}")
    elif command == "defi":
        for defi in ctx.gatherer.defis:
            print(f"{defi['path']} at {defi['offset']}: {defi['mod_name']}?{defi['name']} {defi['lang']} \"{defi['string']}\"")
    elif command == "trefi":
        for trefi in ctx.gatherer.trefis:
            print(f"{trefi['path']} at {trefi['offset']}: {trefi['mod_name']} {trefi['mod_type']} {trefi['lang']}")
    elif command == "symi":
        for symi in ctx.gatherer.symis:
            noverbtostr = lambda symi : repr(symi["noverb"]).replace(", ", ",")
            print(f"{symi['path']} at {symi['offset']}: {symi['mod_name']}?{symi['name']} {symi['type']} noverb={noverbtostr(symi)} align={symi['align']}")
    elif command == "sigfile":
        for sigf in ctx.gatherer.sigfiles:
            print(f"{sigf['path']}: name={sigf['mod_name']} type={sigf['type']} align={repr(sigf['align'])}")
    elif command == "langfile":
        for langf in ctx.gatherer.langfiles:
            print(f"{langf['path']}: {langf['mod_name']} {langf['type']} {langf['lang']}")
