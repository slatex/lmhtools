import re


TOKEN_BEGIN_MHMODNL  = 1
TOKEN_END_MHMODNL    = 2
TOKEN_DEFI           = 3
TOKEN_BEGIN_GVIEWNL  = 4
TOKEN_END_GVIEWNL    = 5
TOKEN_TREFI          = 6
TOKEN_BEGIN_MODSIG   = 7
TOKEN_END_MODSIG     = 8
TOKEN_SYMI           = 9
TOKEN_BEGIN_GVIEWSIG = 10
TOKEN_END_GVIEWSIG   = 11
TOKEN_SYMDEF         = 12
TOKEN_BEGIN_MODULE   = 13
TOKEN_END_MODULE     = 14
TOKEN_IMPORTMHMODULE = 15
TOKEN_USEMHMODULE    = 16
TOKEN_GIMPORT        = 17
TOKEN_GUSE           = 18
TOKEN_MHINPUTREF     = 19

ENV_BEGIN_TOKENS = set([
        TOKEN_BEGIN_MODULE,
        TOKEN_BEGIN_GVIEWSIG,
        TOKEN_BEGIN_GVIEWNL,
        TOKEN_BEGIN_MODSIG,
        TOKEN_BEGIN_MHMODNL])

ENV_END_TOKENS = set([
        TOKEN_END_MODULE,
        TOKEN_END_GVIEWSIG,
        TOKEN_END_GVIEWNL,
        TOKEN_END_MODSIG,
        TOKEN_END_MHMODNL])


# ENV_TOKEN_MAP = {
#     TOKEN_BEGIN_MODULE   : TOKEN_END_MODULE,
#     TOKEN_BEGIN_GVIEWSIG : TOKEN_END_GVIEWSIG,
#     TOKEN_BEGIN_GVIEWNL  : TOKEN_END_GVIEWNL,
#     TOKEN_BEGIN_MODSIG   : TOKEN_END_MODSIG,
#     TOKEN_BEGIN_MHMODNL  : TOKEN_END_MHMODNL,
# }

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

re_defi = re.compile(
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

REGEXES = [
        (re_begin_mhmodnl, TOKEN_BEGIN_MHMODNL),
        (re_end_mhmodnl, TOKEN_END_MHMODNL),
        (re_defi, TOKEN_DEFI),
        (re_begin_gviewnl, TOKEN_BEGIN_GVIEWNL),
        (re_end_gviewnl, TOKEN_END_GVIEWNL),
        (re_tref, TOKEN_TREFI),
        (re_begin_modsig, TOKEN_BEGIN_MODSIG),
        (re_end_modsig, TOKEN_END_MODSIG),
        (re_sym, TOKEN_SYMI),
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


def tokenize(string, regexes):
    '''
    Assumes that regexes is a list of pairs (regex, token_type).
    Returns tokens from a string as pairs (match, token_type),
    sorted according to the match start.
    '''
    tokens = []
    for (regex, token_type) in regexes:
        tokens += [(match, token_type) for match in re.finditer(regex, string)]
    return sorted(tokens, key = lambda e : e[0].start())

