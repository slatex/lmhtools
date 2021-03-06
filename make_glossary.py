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

# alternative environments for definitions
def_alternatives = ["n?omtext", "assertion", "example"]
re_begin_def_alternatives = \
    [re.compile(r"\\begin\s*\{" + e + r"\}\s*(?:\[[^\]]*\])?") for e in def_alternatives]
re_end_def_alternatives = \
    [re.compile(r"\\end\s*\{" + e + r"\}") for e in def_alternatives]

re_trefi1 = re.compile(   # stuff like \trefi{
        r"\\((at|mt|t|Mt|T)ref(i|ii|iii|iv)s?)\{"
        )

re_trefi2 = re.compile(   # stuff like \trefi[?
        r"\\((at|mt|t|Mt|T)ref(i|ii|iii|iv)s?)\[\?"
        )

def findSurroundingEnvironment(string, startregex, endregex, offset):
    begins = [(harvest.get_file_position(string, match.end()), match.end(), 'b') for match in re.finditer(startregex, string)]
    ends = [(harvest.get_file_position(string, match.start()), match.start(), 'e') for match in re.finditer(endregex, string)]
    # TODO: Write a simpler/shorter/more readable algorithm...
    a = sorted(begins + ends, key = lambda t : t[1])
    if not a: return None
    lastOpen = []
    before = True
    left = None
    right = None
    for i in range(len(a)):
        if a[i][0] <= offset:
            if a[i][2] == 'b':
                lastOpen.append(i)
            else:
                if not lastOpen:
                    return None   # TODO: log error
                else:
                    lastOpen = lastOpen[:-1]
        else:
            if before:
                before = False
                if not lastOpen:
                    return None
                left = lastOpen[-1]
                toClose = 0
            if a[i][2] == 'e':
                if toClose:
                    toClose -= 1
                else:
                    right = i
                    break
            else:
                toClose += 1

    if left == None or right == None:
        return None
    else:
        return string[a[left][1]:a[right][1]]



def findSurroundingDefinition(string, offset):
    result = findSurroundingEnvironment(string, re_begin_definition, re_end_definition, offset)
    if result:
        return result
    for (re_begin, re_end) in zip(re_begin_def_alternatives, re_end_def_alternatives):
        result = findSurroundingEnvironment(string, re_begin, re_end, offset)
        if result:
            return result
    return None

class Glossary(object):
    def __init__(self, language, mathhub_dir, uselinks = True):
        self.lang = language
        self.mathhub_dir = mathhub_dir
        self.entries = []
        self.repos = []
        self.covered_defis = set()
        self.uselinks = uselinks

    def fillDefi(self, defi):
        defistr = defi["path"] + defi["offset"]   # unique for each defi
        if defistr in self.covered_defis:
            return
        self.covered_defis.add(defistr)

        isModule = False
        with open(defi["path"], "r") as fp:
            fstr = fp.read()
            filestr = harvest.preprocess_string(fstr)   # removes comments, reduces risk of non-matching file offsets
            if "\\begin{module}" in fstr:
                isModule = True

        offset = defi["offset"]
        defstr = findSurroundingDefinition(filestr, harvest.pos_str_to_int_tuple(offset))
        isError = False
        if not defstr:
            isError = True
            defstr = "\\textcolor{red}{\\textbf{Error: The \\\\defi does not appear to be inside a definition environment. line " + offset + "}}"

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
        self.entries.append(Entry(defi["string"], defstr, repopath, defi["mod_name"], "/".join(postpath)[:-4], isModule, isError, defi["name"]))

    def fill(self, gatherer, allowunknownlang = False):
        for defi in gatherer.defis:
            if defi["lang"] != "?" and defi["lang"] != self.lang:
                continue
            if defi["lang"] == "?" and not allowunknownlang:
                continue
            self.fillDefi(defi)

    def __str__(self):
        if self.uselinks:
            deftoentries = {}
            for e in self.entries:
                if e.isError: continue
                if e.defstr not in deftoentries:
                    deftoentries[e.defstr] = []
                deftoentries[e.defstr].append(e)
            for k in deftoentries:
                displayed = deftoentries[k][0]
                displayed.reffing = "set"
                for e in deftoentries[k][1:]:
                    e.reftargetkey = displayed.keystr
                    if displayed.symbName == e.symbName:
                        e.reffing = "syn"
                    else:
                        e.reffing = "see"



        return ("\\begin{smglossary}\n"
                + "\n\n".join([str(e) for e in sorted(self.entries, key=lambda e : e.keystr)])
                + "\\end{smglossary}\n")


class Entry(object):
    def __init__(self, keystr, defstr, repo, mod_name, pathpart, isModule, isError, symbName):
        self.keystr = keystr
        self.defstr = defstr
        self.repo = repo
        self.mod_name = mod_name
        if self.mod_name[0] == "?":
            raise Exception("weird: " + self.mod_name)
        self.pathpart = pathpart
        for ending in [".en", ".de", ".ru", ".zhs", ".tu", ".ro"]:
            if self.pathpart.endswith(ending):
                self.pathpart = self.pathpart[:-len(ending)]
                break
        self.isModule = isModule
        self.isError = isError
        self.symbName = symbName
        self.reffing = None
        self.reftargetkey = None


    def __str__(self):
        refstr = hex(hash(self.defstr))
        refstr = refstr[refstr.index('x'):]
        keystr = self.keystr
        if self.isModule:
            usestr = "\\usemhmodule[mhrepos=" + self.repo + ",path=" + self.pathpart + "]{" + self.mod_name + "}"
        elif "/" in self.pathpart:
            usestr = "\\usemhmodule[mhrepos=" + self.repo + ",path=" + self.pathpart + ",ext=tex]{" + self.mod_name + "}"
        else:
            usestr = "\\guse[" + self.repo + "]{" + self.mod_name + "}"

        if "$" in keystr and "\\" in keystr:
            keystr =  usestr + keystr
        if self.reffing == "set":
            keystr = "\\hypertarget{" + refstr + "}{" + keystr + "}"
        elif self.reffing == "syn":
            rtk = self.reftargetkey
            if "$" in rtk and "\\" in rtk:
                rtk = usestr + rtk
            return "\\smsynonymref{" + keystr + "}{" + refstr + "}{" + rtk + "}\n"
        elif self.reffing == "see":
            rtk = self.reftargetkey
            if "$" in rtk and "\\" in rtk:
                rtk = usestr + rtk
            return "\\smjointdefref{" + keystr + "}{" + refstr + "}{" + rtk + "}\n"



        return ("\\begin{smentry}{"
                + keystr + "}{"
                + self.repo + "}"
                + "\n" + usestr + "\n"
                + self.defstr.strip() + "\n"
                + "\\end{smentry}\n")


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
