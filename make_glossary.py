#!/usr/bin/env python3

r"""
Sketch:

    forall defis (sorted alphabetically):
    write the defi string (e.g. as \subsection*)
    \gimport the signature file
    find the first \begin{definition}[...] before the defi and the first \end{definition} after it.
    write the content of the definition environment

run this from https://gl.mathhub.info/smglom/meta-inf/applications (i.e. create subdir applications, clone lmhtools in there and create pdf using Makefile)
"""


EXTRA_HEADER = r"""
    \def\fp{\mathfrak{p}}
    \usepackage{ed}
    \def\approxeqOp\approx
"""

import lmh_harvest as harvest
import re
import os
from make_dictionary import LANG2LABEL, LANG2BABEL

re_begin_definition = re.compile(
        r"\\begin\s*"
        r"\{definition\}\s*"
        r"(?:\[[^\]]*\])?"       # optional parameters
        )

re_end_definition = re.compile(
        r"\\end\s*"
        r"\{definition\}"
        )

re_trefi1 = re.compile(   # stuff like \trefi{
        r"\\((at|mt|t|Mt|T)ref(i|ii|iii|iv)s?)\{"
        )

re_trefi2 = re.compile(   # stuff like \trefi[?
        r"\\((at|mt|t|Mt|T)ref(i|ii|iii|iv)s?)\[\?"
        )

def findSurroundingDefinition(string, offset):
    begins = [(harvest.get_file_position(string, match.start()), match.start()) for match in re.finditer(re_begin_definition, string)]
    ends = [(harvest.get_file_position(string, match.end()), match.end()) for match in re.finditer(re_end_definition, string)]
    # find relevant begin/end
    begins = [(p,o) for (p,o) in begins if p < offset]
    ends = [(p,o) for (p,o) in ends if p > offset]
    if len(begins) == 0 or len(ends) == 0:
        return "Error: The \\defi does not appear to be inside a definition environment"
    return string[begins[-1][1]:ends[0][1]]    # without definition environment


class Glossary(object):
    def __init__(self, language, mathhub_dir):
        self.lang = language
        self.mathhub_dir = mathhub_dir
        self.entries = []
        self.repos = []

    def fill(self, gatherer):
        for defi in gatherer.defis:
            if defi["lang"] != self.lang:
                continue
            with open(defi["path"], "r") as fp:
                filestr = harvest.preprocess_string(fp.read())   # removes comments, reduces risk of non-matching file offsets
            defstr = findSurroundingDefinition(filestr, harvest.pos_str_to_int_tuple(defi["offset"]))

            repopath = os.path.relpath(os.path.realpath(defi["path"]), self.mathhub_dir).split(os.sep)
            if "source" in repopath:
                repopath.remove("source")
            repopath = "/".join(repopath[:-1])
            if repopath not in self.repos:
                self.repos.append(repopath)

            self.entries.append(Entry(defi["string"], defstr, repopath, defi["mod_name"]))

    def __str__(self):
        sellang = ""
        if self.lang in LANG2BABEL:
            if self.lang == "en":
                langstr = "\\usepackage[english]{babel}\n"
            else:
                langstr = "\\usepackage[main=english," + LANG2BABEL[self.lang] + "]{babel}\n"
                sellang = "\\selectlanguage{" + LANG2BABEL[self.lang] + "}\n"
        elif self.lang in ["zhs", "zht"]:
            langstr = "\\usepackage{fontspec}\n"
            langstr += "\\setmainfont[AutoFakeBold=4]{FandolFang}\n"
        return ("\\documentclass{article}\n"
                + EXTRA_HEADER +
                "\\usepackage{calbf}\n"
                "\\usepackage[mh]{smglom}\n"
                "\\defpath{MathHub}{" + self.mathhub_dir + "}\n"
                "\\mhcurrentrepos{" + ",".join(sorted(self.repos)) + "}\n"
                "\\usepackage[utf8]{inputenc}\n"
                + langstr +
                "\\title{Glossary (Auto-Generated)}\n"
                "\\begin{document}\n"
                "\\maketitle\n\n"
                + sellang
                + "\n\n".join([str(e) for e in sorted(self.entries, key=lambda e : e.keystr)])
                + r"\end{document}")

            

class Entry(object):
    def __init__(self, keystr, defstr, repo, mod_name):
        self.keystr = keystr
        self.defstr = defstr
        self.repo = repo
        self.mod_name = mod_name
        if self.mod_name[0] == "?":
            raise Exception("weird: " + self.mod_name)

    def __str__(self):
        gimport = "\\gimport[" + self.repo + "]{" + self.mod_name + "}\n"
        # defstr = re_trefi1.sub(r"\\\1[" + self.mod_name + "]{", self.defstr)
        # defstr = re_trefi2.sub(r"\\\1[" + self.mod_name + "?", defstr)
        defstr = self.defstr
        return (
            #(gimport if "$" in self.defstr else "")  # hack to avoid unnecessary gimports (which slow down compilation)
            gimport
            + r"\subsubsection*{" + self.keystr + "}\n"
            + defstr)




if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Script for creating a glossary from e.g. smglom")
    parser.add_argument("LANGUAGE", help="language of the glossary (e.g. en)")
    parser.add_argument("DIRECTORY", nargs="+", help="git repo or higher level directory from which the glossary is generated")

    args = parser.parse_args()

    mathhub_dir = harvest.get_mathhub_dir(args.DIRECTORY[0])
    lang = args.LANGUAGE
    logger = harvest.SimpleLogger(0)   # for now: 0 verbosity
    ctx = harvest.HarvestContext(logger, harvest.DataGatherer(), mathhub_dir)
    for directory in args.DIRECTORY:
        harvest.gather_data_for_all_repos(directory, ctx)
    
    glossary = Glossary(lang, mathhub_dir)
    glossary.fill(ctx.gatherer)
    print(glossary)
