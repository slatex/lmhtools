#!/usr/bin/env python3

"""
Can be used to harvest sTeX data from MathHub.

It was originally created to gather data about SMGloM,
but other sTeX files are increasingly supported.
Data is gathered about introduced symbols, their verbalizations,
trefis, imports, as well as modules and many more things.

The main intention of this script is to serve as a library
for other scripts (e.g. lmh_stats.py and lmh_debug.py).
Nevertheless, it can also be run in stand-alone mode
and output the gathered data.

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

def pos_str_to_int_tuple(offset_string):
    l = offset_string.split(":")
    assert len(l) == 2
    return (int(l[0]), int(l[1]))

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
        self.something_was_logged = False

    def format_filepos(self, path, offset=None, with_col=False):
        # return (path + ":" + offset if offset else path) + (":" if with_col else "")
        # with_col ignored (for emacs we always need it)
        return f"{os.path.abspath(path)}:{offset if offset else 1}:"

    def log(self, message, minverbosity=1, filepath=None, offset=None):
        if self.verbosity < minverbosity:
            return False
        
        if filepath:
            print(f"{self.format_filepos(filepath, offset, True)} {message}\n")
        else:
            print(f"{message}")

        self.something_was_logged = True
        return True


class HarvestContext(object):
    """ The HarvestContext keeps (among other things) data about 'what' is currently processed.
        This includes things like the current repository, file name, ...
        It also has a reference to the DataGatherer. """
    def __init__(self, logger, gatherer, mathhub_path = None): 
        self.logger = logger
        self.gatherer = gatherer

        self.mod_name = None
        self.mod_type = None
        self.repo = None
        self.lang = None
        self.file = None
        self.mathhub_path = mathhub_path

    def log(self, message, minverbosity=1, offsetstr=None, forfile = True):
        self.logger.log(message, minverbosity,
                        filepath=self.file if forfile else None,
                        offset=offsetstr)

class DataGatherer(object):
    """ The DataGatherer collects all the data from the files """
    def __init__(self):
        self.defis = []
        self.trefis = []
        self.symis = []
        self.gimports = []         # also contains guses!
        self.sigfiles = []
        self.langfiles = []
        self.textfiles = []
        self.modules = []
        self.repos = []
        self.importmhmodules = []  # also contains usemhmodules!
        self.mhinputrefs = []      # also contains inputs!

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

    def push_trefi(self, name, targetmodule, isdrefi, offset_str, ctx):
        self.trefis.append(
            {
                "mod_name" : ctx.mod_name,
                "mod_type" : ctx.mod_type,
                "repo" : ctx.repo,
                "offset" : offset_str,
                "lang" : ctx.lang,
                "path" : ctx.file,
                "name" : name,
                "target_mod" : (targetmodule if targetmodule else ctx.mod_name),
                "drefi" : isdrefi,
            }
        )

    def push_importmhmodule(self, repo, file_, type_, ctx):  # also for usemhmodule
        self.importmhmodules.append(
            {
                "mod_name" : ctx.mod_name,  # can be None
                "repo" : ctx.repo,
                "path" : ctx.file,
                "type" : type_,    # "usemhmodule" or "importmhmodule"
                "dest_repo" : repo,
                "dest_path" : file_,
            }
        )

    def push_mhinputref(self, repo, file_, ctx):  # also for input
        self.mhinputrefs.append(
            {
                "mod_name" : ctx.mod_name,  # can be None
                "repo" : ctx.repo,
                "path" : ctx.file,
                "dest_repo" : repo,
                "dest_path" : file_,
            }
        )

    def push_textfile(self, ctx):
        self.textfiles.append(
            {
                "repo" : ctx.repo,
                "path" : ctx.file,
            }
        )

    def push_gimport(self, repo, mod_name, type_, ctx):  # also for guses
        self.gimports.append(
            {
                "mod_name" : ctx.mod_name,
                "mod_type" : ctx.mod_type,
                "repo" : ctx.repo,
                "path" : ctx.file,
                "type" : type_,     # "guse" or "gimport"
                "dest_repo" : repo,
                "dest_mod" : mod_name,
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
TOKEN_IMPORTMHMODULE = 14
TOKEN_USEMHMODULE    = 15
TOKEN_GIMPORT        = 16
TOKEN_GUSE           = 17
TOKEN_MHINPUTREF     = 18

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
        r"\\(?P<start>at|mt|t|Mt|T|d|D)ref(?P<arity>i|ii|iii|iv)s?\s*"
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
        r"\{(?P<name>[\w\.-]+)\}"                   # name
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

re_importmhmodule = re.compile(
        r"\\importmhmodule\s*"
        r"(?:\[(?P<params>[^\]]*)\])?\s*"          # parameters
        r"\{(?P<arg>" + re_arg + r")\}"            # arg
        )

re_usemhmodule = re.compile(
        r"\\usemhmodule\s*"
        r"(?:\[(?P<params>[^\]]*)\])?\s*"          # parameters
        r"\{(?P<arg>" + re_arg + r")\}"            # arg
        )

re_gimport = re.compile(
        r"\\gimport(\*)?\s*"
        r"(?:\[(?P<params>[^\]]*)\])?\s*"          # parameter
        r"\{(?P<arg>" + re_arg + r")\}"            # arg
        )

re_guse = re.compile(
        r"\\guse\s*"
        r"(?:\[(?P<params>[^\]]*)\])?\s*"          # parameter
        r"\{(?P<arg>" + re_arg + r")\}"            # arg
        )

re_mhinputref = re.compile(
        r"\\(mhinputref|input)\s*"
        r"(?:\[(?P<params>[^\]]*)\])?\s*"          # parameters
        r"\{(?P<arg>" + re_arg + r")\}"            # arg
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
        (re_importmhmodule, TOKEN_IMPORTMHMODULE),
        (re_usemhmodule, TOKEN_USEMHMODULE),
        (re_gimport, TOKEN_GIMPORT),
        (re_guse, TOKEN_GUSE),
        (re_mhinputref, TOKEN_MHINPUTREF),
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
                ctx.log(f"Require \\begin{{modsig}} or \\begin{{gviewsig}} before token: '{match.group(0)}'",
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
        elif token_type == TOKEN_GIMPORT:
            repo = ctx.repo
            repo_param = match.group("params")
            if repo_param:
                repo = os.path.join(ctx.mathhub_path, repo_param)
            mod_name = match.group("arg")
            ctx.gatherer.push_gimport(repo, mod_name, "gimport", ctx)
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
                ctx.log(f"Require \\begin{{mhmodnl}} before token: '{match.group(0)}'",
                        1, get_file_pos_str(string, match.start()))
                continue
            params = get_params(match.group("params"))

            args = get_args(match, False, string, ctx)

            tname = params["name"] if "name" in params else "-".join(args)
            val  = " ".join(args)

            ctx.gatherer.push_defi(tname, val, get_file_pos_str(string, match.start()), ctx, params)
        elif token_type == TOKEN_TREF:
            if required_end_module == None:
                ctx.log(f"Require \\begin{{mhmodnl}} or \\begin{{gviewnl}} before token: '{match.group(0)}'",
                        1, get_file_pos_str(string, match.start()))
                continue
            params = match.group("params")
            args = get_args(match, False, string, ctx)
            isdrefi = "d" in match.group("start").lower()

            tname = "-".join(args)
            targetmodule = None
            if params:
                targetmodule = params
                if "?" in params:
                    targetmodule = params.split("?")[0]
                    tname = params.split("?")[1]
                    if not "m" in match.group("start").lower():
                        ctx.log(f"Expected mtrefi for '{match.group(0)}'", 1,
                                get_file_pos_str(string, match.start()))

            ctx.gatherer.push_trefi(tname, targetmodule, isdrefi, get_file_pos_str(string, match.start()), ctx)
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
        elif token_type == TOKEN_GUSE:
            repo = ctx.repo
            repo_param = match.group("params")
            if repo_param:
                repo = os.path.join(ctx.mathhub_path, repo_param)
            mod_name = match.group("arg")
            ctx.gatherer.push_gimport(repo, mod_name, "guse", ctx)
        else:
            ctx.log(f"Unexpected token: '{match.group(0)}'", 2, get_file_pos_str(string, match.start()))

    if required_end_module:
        ctx.log("\\end{gviewnl} or \\end{mhmodnl} missing", 1)
        return

    if not isacceptablefile:
        ctx.log("File didn't have \\begin{mhmodnl} or \\begin{gviewnl}", 1)
        return

    ctx.gatherer.push_langfile(ctx)

def harvest_mono(string, name, ctx):
    """ harvests the data from file content """

    tokens = parse(string, regexes)
    if len(tokens) == 0:
        ctx.log("No matches found in file", 2)
        return

    in_module = 0
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
                        2, get_file_pos_str(string, match.start()))
                continue
            params = match.group("params")
            args = get_args(match, False, string, ctx)
            isdrefi = "d" in match.group("start").lower()

            tname = "-".join(args)
            targetmodule = None
            if params:
                targetmodule = params
                if "?" in params:
                    targetmodule = params.split("?")[0]
                    tname = params.split("?")[1]
                    if not "m" in match.group("start").lower():
                        ctx.log(f"Expected mtrefi for '{match.group(0)}'", 1,
                                get_file_pos_str(string, match.start()))

            ctx.gatherer.push_trefi(tname, targetmodule, isdrefi, get_file_pos_str(string, match.start()), ctx)
        elif token_type in [TOKEN_IMPORTMHMODULE, TOKEN_USEMHMODULE, TOKEN_MHINPUTREF]:
            if not in_module:
                if token_type == TOKEN_IMPORTMHMODULE:
                    ctx.log("Require \\begin{module} before token: '" + match.group(0) + "'",
                            2, get_file_pos_str(string, match.start()))
                    continue
            params = get_params(match.group("params"))
            repo = ctx.repo
            if "repos" in params:
                repo = os.path.join(ctx.mathhub_path, params["repos"])
            file_name = match.group("arg") + ".tex"
            if token_type == TOKEN_MHINPUTREF:
                path = os.path.join(repo, "source", file_name)
            elif "path" in params:
                path = os.path.join(repo, "source", params["path"]) + ".tex"
            else:
                path = os.path.join(os.path.split(ctx.file)[0], file_name)
            if token_type == TOKEN_IMPORTMHMODULE:
                ctx.gatherer.push_importmhmodule(repo, path, "importmhmodule", ctx)
            elif token_type == TOKEN_USEMHMODULE:
                ctx.gatherer.push_importmhmodule(repo, path, "usemhmodule", ctx)
            elif token_type == TOKEN_MHINPUTREF:
                ctx.gatherer.push_mhinputref(repo, path, ctx)
        elif token_type == TOKEN_BEGIN_MODULE:
            if in_module:
                ctx.log("Nested modules are not yet fully supported",
                        2, get_file_pos_str(string, match.start()))
                in_module += 1
                continue

            in_module += 1
            ctx.lang = "?"
            params = get_params(match.group("params"))
            if "id" in params:
                ctx.mod_name = params["id"]
                in_named_module = True
                if ctx.mod_name != name:
                    ctx.log(f"Name '{params['id']}' does not match file name", 2, get_file_pos_str(string, match.start()))
            else:
                ctx.log("Warning: Inferring module id from file name", 2, get_file_pos_str(string, match.start()))
                ctx.mod_name = os.path.split(ctx.file)[1][:-4]
                # in_named_module = False
                in_named_module = True
            ctx.mod_type = "module"
        elif token_type == TOKEN_END_MODULE:
            in_module -= 1
            if in_module == 0 and in_named_module:
                ctx.gatherer.push_module(ctx)
                in_named_module = False
        elif token_type == TOKEN_GUSE or token_type == TOKEN_GIMPORT:
            repo = ctx.repo
            repo_param = match.group("params")
            if repo_param:
                repo = os.path.join(ctx.mathhub_path, repo_param)
            mod_name = match.group("arg")
            ctx.gatherer.push_gimport(repo, mod_name, {TOKEN_GUSE : "guse", TOKEN_GIMPORT : "gimport"}[token_type], ctx)
        else:
            if token_type == TOKEN_SYMDEF and in_named_module:
                continue
            ctx.log(f"Unexpected token: '{match.group(0)}'", 2, get_file_pos_str(string, match.start()))

    if in_module:
        ctx.log("\\end{module} missing", 1)
        return

def harvest_text(string, ctx):
    """ harvests the trefis etc. from unidentified file content """

    tokens = parse(string, regexes)
    assert ctx.mod_name == None
    ctx.gatherer.push_textfile(ctx)

    for (match, token_type) in tokens:
        if token_type == TOKEN_TREF:
            #ctx.log("Warning: Found trefi token in unidentified file",
            #        3, get_file_pos_str(string, match.start()))
            params = match.group("params")
            args = get_args(match, False, string, ctx)
            isdrefi = "d" in match.group("start").lower()

            tname = "-".join(args)
            targetmodule = None
            if params:
                targetmodule = params
                if "?" in params:
                    targetmodule = params.split("?")[0]
                    tname = params.split("?")[1]
                    if not "m" in match.group("start").lower():
                        ctx.log(f"Expected mtrefi for '{match.group(0)}'", 1,
                                get_file_pos_str(string, match.start()))

            ctx.gatherer.push_trefi(tname, targetmodule, isdrefi, get_file_pos_str(string, match.start()), ctx)
        elif token_type == TOKEN_USEMHMODULE or token_type == TOKEN_MHINPUTREF:
            params = get_params(match.group("params"))
            repo = ctx.repo
            if "repos" in params:
                repo = os.path.join(ctx.mathhub_path, params["repos"])
            file_name = match.group("arg") + ".tex"
            if token_type == TOKEN_MHINPUTREF:
                path = os.path.join(repo, "source", file_name)
            elif "path" in params:
                path = os.path.join(repo, "source", params["path"]) + ".tex"
            else:
                path = os.path.join(os.path.split(ctx.file)[0], file_name)
            if token_type == TOKEN_USEMHMODULE:
                ctx.gatherer.push_importmhmodule(repo, path, "usemhmodule", ctx)
            elif token_type == TOKEN_MHINPUTREF:
                ctx.gatherer.push_mhinputref(repo, path, ctx)
        elif token_type == TOKEN_GUSE:
            repo = ctx.repo
            repo_param = match.group("params")
            if repo_param:
                repo = os.path.join(ctx.mathhub_path, repo_param)
            mod_name = match.group("arg")
            ctx.gatherer.push_gimport(repo, mod_name, "guse", ctx)
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

def harvest_file(root, file_name, ctx):
    m = harvest_file.file_regex.match(file_name)
    if m == None:
        return
    name = m.group("name")
    lang = m.group("lang")
    full_name = name
    if lang: full_name += "." + lang

    file_path = os.path.join(root, f"{name}.{lang}.tex" if lang else f"{name}.tex")
    if name in ["all", "localpaths"]:
        return

    with open(file_path, "r") as fp:
        ctx.file = file_path
        ctx.mod_name = None
        ctx.mod_type = None
        try:
            string = preprocess_string(fp.read())
            file_type = identify_file(string)
            if not file_type:
                ctx.mod_type = "text"
                harvest_text(string, ctx)
            elif file_type == "nl":
                if lang:
                    harvest_nl(string, name, lang, ctx)
                else:
                    ctx.log("It appears to be a language file, but the filename doesn't indicate that", 2)
            elif lang and file_type != "nl" and len(lang) in [2,3]:
                ctx.log("Doesn't appear to be a language file - skipping it", 2)
                return
            elif file_type == "sig":
                harvest_sig(string, full_name, ctx)
            elif file_type == "mono":
                harvest_mono(string, full_name, ctx)
            else:
                raise Exception("An internal error occured while trying to identify the file")
        except Exception as ex:
            ctx.log(f"An internal error occured during processing:\n'{exception_to_string(ex)}'", 0)
            return

harvest_file.file_regex = re.compile(r"^(?P<name>[a-zA-Z0-9-]+)(\.(?P<lang>[a-zA-Z]+))?\.tex$")


def gather_data_for_repo(repo_directory, ctx):
    harvest_repo_metadata(repo_directory, ctx)
    dir_path = os.path.join(repo_directory, "source")
    for root, dirs, files in os.walk(dir_path):
        for file_name in files:
            harvest_file(root, file_name, ctx)

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

def get_mathhub_dir(path, mayContainSymbLinks = True):
    """ Extracts the MathHub directory from a path """
    mathhub_dir = os.path.abspath(path)
    while not mathhub_dir.endswith("MathHub"):
        new = os.path.split(mathhub_dir)[0]
        if new == mathhub_dir:  # reached root
            if mayContainSymbLinks:
                return get_mathhub_dir(os.path.realpath(path), False)
            raise Exception("Failed to infer MathHub directory (it is required that a parent directory called 'MathHub' exists)")
        mathhub_dir = new
    return mathhub_dir

def split_path_repo_doc(path):
    """ splits a path into repository name and document path (relative to 'source') """
    path = os.path.realpath(path)
    mathhub_dir = get_mathhub_dir(path)
    restpath = os.path.relpath(path, mathhub_dir).split(os.sep)
    if "source" not in restpath:
        raise Exception("Couldn't find a 'source' folder in " + path)
    repo = os.sep.join(restpath[:restpath.index("source")])
    doc = os.sep.join(restpath[restpath.index("source")+1:])
    if doc.endswith(".tex"):
        doc = doc[:-4]
    return repo, doc


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Script for gathering MathHub data",
            epilog="Example call: lmh_harvest.py -v1 defi /path/to/MathHub/smglom")
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

    mathhub_dir = get_mathhub_dir(args.DIRECTORY[0])
    logger = SimpleLogger(verbosity)
    ctx = HarvestContext(logger, DataGatherer(), mathhub_dir)

    for directory in args.DIRECTORY:
        gather_data_for_all_repos(directory, ctx)

    if verbosity >= 2 or logger.something_was_logged:
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
