#!/usr/bin/env python3

"""
Can be used to create a multi-lingual dictionary from e.g. smglom
"""

LANG2BABEL = {
    "de" : "german",
    "en" : "english",
    "fr" : "french",
    "ro" : "romanian",
    "zhs" : "chinese-simplified",
    "zht" : "chinese-traditional",
        }

import os
import lmh_harvest as harvest

class Dictionary(object):
    """ Container for collecting the dictionary content"""
    def __init__(self, languages, mathhub_dir):
        self.languages = languages
        self.mathhub_dir = mathhub_dir
        self.data = {l : {} for l in languages}
    
    def addEntry(self, symbol, language, string):
        assert language in self.languages
        if symbol not in self.data[language]:
            self.data[language][symbol] = []
        self.data[language][symbol].append(string)

    def getEntries(self, keylang, otherlangs):
        allSymbols = set([symb for language in self.languages for symb in self.data[language]])

        entries = []
        for symb in allSymbols:
            if symb not in self.data[keylang]:
                continue
            for keyString in self.data[keylang][symb]:
                entries.append(Entry(keyString, [", ".join(self.data[lang][symb]) if symb in self.data[lang] else "" for lang in otherlangs], symb))
        return sorted(entries, key=lambda e : e.keystr.lower())

class Entry(object):
    def __init__(self, keystr, transl, symb):
        self.keystr = keystr
        self.transl = transl
        self.gimport = r"\gimport[" + symb[0] + "]{" + symb[1] + "}"
        self.repo = symb[0]

def makeDictionary(mathhub_dir, gatherer, languages):
    dictionary = Dictionary(languages, mathhub_dir)

    for defi in gatherer.defis:
        if defi["lang"] not in languages:
            continue
        gimportpath = os.path.relpath(os.path.realpath(defi["path"]), mathhub_dir).split(os.sep)
        if "source" in gimportpath:
            gimportpath.remove("source")
        gimportpath = "/".join(gimportpath[:-1])
        symb = (gimportpath, defi["mod_name"], defi["name"])
        dictionary.addEntry(symb, defi["lang"], defi["string"])

    return dictionary

def getRepos(entries):
    return sorted(list(set([entry.repo for entry in entries])))

def printLaTeXHeader(dictionary):
    # TODO: we only calculate entries here to extract repos (unnecessary!)
    entries = dictionary.getEntries(dictionary.languages[0], dictionary.languages[1:])
    langLabels = [(LANG2BABEL[l] if l in LANG2BABEL else l).capitalize() for l in dictionary.languages]

    print(r"\documentclass{article}")
    print(r"\usepackage[mh]{smglom}")
    print(r"\defpath{MathHub}{" + dictionary.mathhub_dir + "}")
    print(r"\mhcurrentrepos{" + ",".join(getRepos(entries)) + "}")
    print(r"\usepackage{fullpage}")
    print(r"\usepackage[utf8]{inputenc}")
    #print(r"\usepackage[main=" + ",".join([LANG2BABEL[l] for l in dictionary.languages if l in LANG2BABEL]) + "]{babel}")
    babellangs = [LANG2BABEL[l] for l in dictionary.languages if l in LANG2BABEL]
    if "english" in babellangs:
        babellangs.remove("english")
    print(r"\usepackage[main=english," + ",".join(babellangs) + "]{babel}")
    print(r"\usepackage{longtable}")
    print(r"\title{Multi-Lingual Dictionary (Auto-Generated)\\")
    print(r"\small{Languages: " + ", ".join(langLabels) + r"}\\")
    print(r"\small{Topics: " + ", ".join(sorted([r.split("/")[-1].capitalize() for r in getRepos(entries)])) + r"}}")
    print(r"\begin{document}")
    print(r"\maketitle")
    print(r"\tableofcontents")

def printAsLaTeX(dictionary):
    assert len(dictionary.languages) > 0
    printLaTeXHeader(dictionary)
    for keylang in dictionary.languages:
        otherlangs = dictionary.languages[:]
        otherlangs.remove(keylang)
        langLabels = [(LANG2BABEL[l] if l in LANG2BABEL else l).capitalize() for l in [keylang] + otherlangs]
        print(r"\section{" + langLabels[0] + "}")
        print(r"\begin{longtable}{" + "".join(["p{" + str(0.99/len(dictionary.languages)) + r"\textwidth}"] * len(dictionary.languages)) + "}")
        print("&".join(["\\textbf{" + l + "}" for l in langLabels]) + r"\\")
        print(r"\hline")
        for entry in dictionary.getEntries(keylang, otherlangs):
            # print(entry.gimport)
            cells = [entry.keystr] + entry.transl
            cells = ["\\selectlanguage{" + LANG2BABEL[l] + "}" + c if l in LANG2BABEL else c for (l,c) in zip([keylang] + otherlangs, cells)]
            # only have gimport if $ in entry (to avoid unnecessary gimports, which significantly slow down the compilation)
            cells = [entry.gimport + c if "$" in c else c for c in cells]
            print("&".join(cells) + r"\\")
        print(r"\end{longtable}")
    print(r"\end{document}""")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Script for creating a multi-lingual dictionary from e.g. smglom",
            epilog="Example call: ")    # TODO: example call
    parser.add_argument("LANGUAGES", help="languages to be included in dictionary (example value: en,de,ro")
    parser.add_argument("DIRECTORY", nargs="+", help="git repo or higher level directory for which dictionary is generated")

    args = parser.parse_args()

    mathhub_dir = harvest.get_mathhub_dir(args.DIRECTORY[0])
    languages = args.LANGUAGES.split(",")
    logger = harvest.SimpleLogger(0)   # for now: 0 verbosity
    ctx = harvest.HarvestContext(logger, harvest.DataGatherer(), mathhub_dir)
    for directory in args.DIRECTORY:
        harvest.gather_data_for_all_repos(directory, ctx)
    
    dictionary = makeDictionary(mathhub_dir, ctx.gatherer, languages)
    # printAsTxt(dictionary)
    printAsLaTeX(dictionary)

