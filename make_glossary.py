#!/usr/bin/env python3

r"""
    Functionality for creating an sTeX-based glossary.
    It can be run directly on smglom.
    The functionality is also used in lecture_glossary.py,
    which gathers symbols used in a lecture and creates a glossary from that.

Sketch:

    forall defis (sorted alphabetically):
    write the defi string (e.g. as \subsection*)
    \gimport the signature file
    find the first \begin{definition}[...] before the defi and the first \end{definition} after it.
    write the content of the definition environment

run this from https://gl.mathhub.info/smglom/meta-inf/applications (i.e. create subdir applications, clone lmhtools in there and create pdf using Makefile)
"""


HEADER = r"""
\newenvironment{entry}[2]%
{\item[#1]\mhcurrentrepos{#2}\begin{module}[id=foo]\begin{definition}[display=flow]}
{\end{definition}\end{module}}
\newenvironment{entrynl}[4]%
{#4\item[#1]\mhcurrentrepos{#2}\begin{mhmodnl}#3\begin{definition}[display=flow]}
{\end{definition}\end{mhmodnl}}
\newenvironment{smglossary}{\begin{itemize}}{\end{itemize}}

\usepackage{tikz}
\usepackage[mh]{smglom}
\usepackage{omdoc}

% \input{localpaths}
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
    begins = [(harvest.get_file_position(string, match.end()), match.end()) for match in re.finditer(re_begin_definition, string)]
    ends = [(harvest.get_file_position(string, match.start()), match.start()) for match in re.finditer(re_end_definition, string)]
    # find relevant begin/end
    begins = [(p,o) for (p,o) in begins if p < offset]
    ends = [(p,o) for (p,o) in ends if p > offset]
    if len(begins) == 0 or len(ends) == 0:
        return "\\textcolor{red}{\\textbf{Error: The \\\\defi does not appear to be inside a definition environment}}"
    return string[begins[-1][1]:ends[0][1]]    # without definition environment


class Glossary(object):
    def __init__(self, language, mathhub_dir, preamblepath = None):
        self.lang = language
        self.mathhub_dir = mathhub_dir
        self.entries = []
        self.repos = []
        self.covered_defis = set()
        self.preamblepath = preamblepath

    def fillDefi(self, defi):
        defistr = defi["path"] + defi["offset"]   # unique for each defi
        if defistr in self.covered_defis:
            return
        self.covered_defis.add(defistr)

        with open(defi["path"], "r") as fp:
            filestr = harvest.preprocess_string(fp.read())   # removes comments, reduces risk of non-matching file offsets
        defstr = findSurroundingDefinition(filestr, harvest.pos_str_to_int_tuple(defi["offset"]))

        repopath = os.path.relpath(os.path.realpath(defi["path"]), self.mathhub_dir).split(os.sep)
        postpath = None
        if "source" in repopath:
            # repopath.remove("source")
            postpath = repopath[repopath.index("source")+1:]
            repopath = repopath[:repopath.index("source")]
        else:
            print("WARNING: path doesn't contain 'source' folder - skipping it: " + repopath)
            return
        repopath = os.sep.join(repopath)
        if repopath not in self.repos:
            self.repos.append(repopath)
        importstr = ""
        self.entries.append(Entry(defi["string"], defstr, repopath, importstr, defi["mod_name"], defi["lang"], "/".join(postpath)[:-4]))

    def fill(self, gatherer, allowunknownlang = False):
        for defi in gatherer.defis:
            if defi["lang"] != "?" and defi["lang"] != self.lang:
                continue
            if defi["lang"] == "?" and not allowunknownlang:
                continue
            self.fillDefi(defi)

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
            langstr += "\\XeTeXlinebreaklocale \"zh\"\n"
            langstr += "\\XeTeXlinebreakskip = 0pt plus 1pt minus 0.1pt\n"

        preamblestuff = ""
        if self.preamblepath:
            p = os.path.split(os.path.split(os.path.relpath(self.preamblepath, self.mathhub_dir))[0])[0]
            preamblestuff = f"\\mhcurrentrepos{{{p}}}\n"
            preamblestuff += f"\\input{{{self.preamblepath}}}\n"
        return ("\\documentclass{article}\n"
                + HEADER
                + "\\defpath{MathHub}{" + self.mathhub_dir + "}\n"
                + preamblestuff
                + langstr
                + "\\title{Glossary (Auto-Generated)}\n"
                "\\begin{document}\n"
                "\\maketitle\n\n"
                + sellang
                + "\\begin{smglossary}\n"
                + "\n\n".join([str(e) for e in sorted(self.entries, key=lambda e : e.keystr)])
                + "\\end{smglossary}\n"
                + r"\end{document}")


class Entry(object):
    def __init__(self, keystr, defstr, repo, importstr, mod_name, lang, pathpart):
        self.keystr = keystr
        self.defstr = defstr
        self.importstr = importstr
        self.repo = repo
        self.mod_name = mod_name
        if self.mod_name[0] == "?":
            raise Exception("weird: " + self.mod_name)
        self.lang = lang
        if self.lang == "?":
            self.lang = "en"
        self.pathpart = pathpart
        self.usemhmodnl = False
        if self.pathpart.endswith("." + self.lang):
            self.usemhmodnl = True
            self.pathpart = self.pathpart[:-len("." + self.lang)]


    def __str__(self):
        gimport = ""
        if "$" in self.keystr and "\\" in self.keystr:
            gimport = "\\gimport[" + self.repo + "]{" + self.mod_name + "}"
        if self.usemhmodnl:
            return ("\\begin{entrynl}{"
                    + self.keystr + "}{" + self.repo + "}{"
                    + f"[path={self.pathpart}]{{{self.mod_name}}}{{{self.lang}}}" + "}{"
                    + gimport + "}"
                    + self.defstr.strip() + "\n"
                    + "\\end{entrynl}\n")
        else:
            return ("\\begin{entry}{"
                    + self.keystr + "}{" + self.repo + "}"
                    + "\n\\usemhmodule[repos=" + self.repo + ",path=" + self.pathpart + "]{" + self.mod_name + "}\n"
                    + self.defstr.strip() + "\n"
                    + "\\end{entry}\n")


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
    
    glossary = Glossary(lang, mathhub_dir, mathhub_dir + "/smglom/meta-inf/lib/preamble")
    glossary.fill(ctx.gatherer)
    print(glossary)
