#!/usr/bin/env python3

"""
Can be used to create a multi-lingual dictionary from e.g. smglom
"""

import lmh_harvest as harvest

class Dictionary(object):
    """ Container for the actual dictionary content"""
    def __init__(self, languages):
        self.languages = languages
        self.keylang = languages[0]
        self.data = {l : {} for l in languages}
    
    def addEntry(self, symbol, language, string):
        assert language in self.languages
        if symbol not in self.data[language]:
            self.data[language][symbol] = []
        self.data[language][symbol].append(string)

    def getEntries(self):
        allSymbols = set([symb for language in self.languages for symb in self.data[language]])
        # only symbols with entry in keylang are relevant
        # relevantSymbols = [symb for symb in allSymbols if symb in self.data[self.keylang]]
        # return sorted([[", ".join(self.data[lang][symb]) if symb in self.data[lang] else "" for lang in self.languages] for symb in relevantSymbols])
        entries = []
        for symb in allSymbols:
            if symb not in self.data[self.keylang]:
                continue
            for keyString in self.data[self.keylang][symb]:
                entries.append([keyString] + [", ".join(self.data[lang][symb]) if symb in self.data[lang] else "" for lang in self.languages[1:]])
        return sorted(entries, key=lambda e : e[0].lower())

def makeDictionary(gatherer, languages):
    dictionary = Dictionary(languages)

    for defi in gatherer.defis:
        if defi["lang"] not in languages:
            continue
        symb = defi["mod_name"]+"?"+defi["name"]
        dictionary.addEntry(symb, defi["lang"], defi["string"])

    return dictionary

def printAsTxt(dictionary):
    width = 30
    print(" ".join([lang.upper().ljust(width) for lang in dictionary.languages]))
    print()
    for entry in dictionary.getEntries():
        print("".join([e.ljust(width) for e in entry]))

def printAsLaTeX(dictionary):
    assert len(dictionary.languages) > 0
    print(r"""\documentclass{article}
\usepackage{fullpage}
\usepackage[utf8]{inputenc}
\usepackage{longtable}
\title{Multi-Lingual Dictionary (Auto-Generated)}
\begin{document}
\maketitle""")
    print(r"\begin{longtable}{" + "".join(["p{" + str(0.99/len(dictionary.languages)) + r"\textwidth}"] * len(dictionary.languages)) + "}")
    print("&".join(dictionary.languages) + r"\\")
    print(r"\hline")
    for entry in dictionary.getEntries():
        print("&".join(entry) + r"\\")
    print(r"""\end{longtable}
\end{document}""")


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
    
    dictionary = makeDictionary(ctx.gatherer, languages)
    # printAsTxt(dictionary)
    printAsLaTeX(dictionary)

