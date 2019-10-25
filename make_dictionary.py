#!/usr/bin/env python3

"""
Can be used to create a multi-lingual dictionary from e.g. smglom
"""

LANG2BABEL = {
    "de" : "german",
    "en" : "english",
    "fr" : "french",
    "ro" : "romanian",
        }

LANG2LABEL = {
    "de" : "German",
    "en" : "English",
    "fr" : "French",
    "ro" : "Romanian",
    "zhs" : "Chinese (simplified)",
    "zht" : "Chinese (traditional)",
        }

import os
import re
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
        repopath = os.path.relpath(os.path.realpath(defi["path"]), mathhub_dir).split(os.sep)
        if "source" in repopath:
            repopath.remove("source")
        repopath = "/".join(repopath[:-1])
        symb = (repopath, defi["mod_name"], defi["name"])
        dictionary.addEntry(symb, defi["lang"], defi["string"])

    return dictionary

def getRepos(entries):
    return sorted(list(set([entry.repo for entry in entries])))

def getLaTeXHeader(dictionary):
    # TODO: we only calculate entries here to extract repos (unnecessary!)
    entries = dictionary.getEntries(dictionary.languages[0], dictionary.languages[1:])
    langLabels = [(LANG2LABEL[l] if l in LANG2LABEL else l).capitalize() for l in dictionary.languages]
    result = ""

    result += r"\documentclass{article}" + "\n"
    result += r"\usepackage{calbf}" + "\n"
    result += r"\usepackage[mh]{smglom}" + "\n"
    result += r"\defpath{MathHub}{" + dictionary.mathhub_dir + "}" + "\n"
    result += r"\mhcurrentrepos{" + ",".join(getRepos(entries)) + "}" + "\n"
    result += r"\usepackage{fullpage}" + "\n"
    result += r"\usepackage[utf8]{inputenc}" + "\n"
    babellangs = [LANG2BABEL[l] for l in dictionary.languages if l in LANG2BABEL]
    # we need English (the dictionary itself is in English)
    if "english" in babellangs:
        babellangs.remove("english")
    result += r"\usepackage[main=english," + ",".join(babellangs) + "]{babel}" + "\n"
    if "zhs" in dictionary.languages or "zht" in dictionary.languages:
    #    result += r"\usepackage{CJKutf8}" + "\n"
    #    result += r"\usepackage[UTF8]{ctex}" + "\n"
        result += r"\usepackage{fontspec}" + "\n"
        # result += r"\setmainfont[AutoFakeBold=4]{FandolFang}" + "\n"
        # result += r'\XeTeXlinebreaklocale "zh"' + "\n"
    result += r"\usepackage{longtable}" + "\n"
    result += r"\title{Multi-Lingual Dictionary (Auto-Generated)\\" + "\n"
    result += r"\small{Languages: " + ", ".join(langLabels) + r"}\\" + "\n"
    result += r"\small{Topics: " + ", ".join(sorted([r.split("/")[-1].capitalize() for r in getRepos(entries)])) + r"}}" + "\n"
    result += r"\begin{document}" + "\n"
    result += r"\maketitle" + "\n"
    result += r"\tableofcontents" + "\n"
    return result

def getAsLaTeX(dictionary):
    assert len(dictionary.languages) > 0
    result = getLaTeXHeader(dictionary)
    for keylang in dictionary.languages:
        otherlangs = dictionary.languages[:]
        otherlangs.remove(keylang)
        langLabels = [(LANG2LABEL[l] if l in LANG2LABEL else l).capitalize() for l in [keylang] + otherlangs]
        result += r"\newpage" + "\n"
        result += "" + "\n"
        result += r"\section{" + langLabels[0] + "}" + "\n"
        result += r"\begin{longtable}{" + "".join(["p{" + str(0.99/len(dictionary.languages)) + r"\textwidth}"] * len(dictionary.languages)) + "}" + "\n"
        result += "&".join(["\\textbf{" + l + "}" for l in langLabels]) + r"\\" + "\n"
        result += r"\hline" + "\n"
        for entry in dictionary.getEntries(keylang, otherlangs):
            cells = [entry.keystr] + entry.transl
            newcells = []
            for (l, c) in zip([keylang] + otherlangs, cells):
                if "$" in c:
                    # only have gimport if $ in entry (to avoid unnecessary gimports, which significantly slow down the compilation)
                    c = entry.gimport + c
                if l in LANG2BABEL:
                    newcells += ["\\selectlanguage{" + LANG2BABEL[l] + "}" + c]
                elif l in ["zhs", "zht"]:
                    # newcells += ["\\begin{CJK}{UTF8}{gbsn}" + c + "\\end{CJK}"]
                    newcells += [r"{\fontspec[AutoFakeBold=4]{FandolFang}" + c + "}"]
                else:
                    newcells += [c]
            result += " & ".join(newcells) + r"\\" + "\n"
        result += r"\end{longtable}" + "\n"
    result += r"\end{document}""" + "\n"
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Script for creating a multi-lingual dictionary from e.g. smglom",
            epilog="Example call: ")    # TODO: example call
    parser.add_argument("LANGUAGES", help="languages to be included in dictionary (example value: en,de,ro")
    parser.add_argument("DIRECTORY", nargs="+", help="git repo or higher level directory for which dictionary is generated")

    args = parser.parse_args()

    mathhub_dir = harvest.get_mathhub_dir(args.DIRECTORY[0])
    languages = re.split("[-,_+.]", args.LANGUAGES)
    logger = harvest.SimpleLogger(0)   # for now: 0 verbosity
    ctx = harvest.HarvestContext(logger, harvest.DataGatherer(), mathhub_dir)
    for directory in args.DIRECTORY:
        harvest.gather_data_for_all_repos(directory, ctx)
    
    dictionary = makeDictionary(mathhub_dir, ctx.gatherer, languages)
    # printAsTxt(dictionary)
    print(getAsLaTeX(dictionary))

