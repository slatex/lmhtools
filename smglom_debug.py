#!/usr/bin/env python3

"""
Can be used to find certain kinds of errors in smglom.

This script analyzes the data collected with smglom_harvet.py
and checks that the data is 'consisten', meaning that
for example every symbol has been introduced in a signature
file etc.
The verbosity level changes what kind of errors are displayed.
"""

import sys
import smglom_harvest as harvest


def partition(entries, key):
    result = {}
    for entry in entries:
        k = key(entry)
        if k not in result:
            result[k] = []
        result[k].append(entry)
    return result

def unique_list(l):
    return sorted(list(set(l)))


def check_data(gatherer, verbosity):
    """ Checks data for errors (but not for things like missing verbalizations) """

    # partition data for efficient look-up
    sigf_part = partition(gatherer.sigfiles, lambda e : (e["repo"], e["mod_name"]))
    langf_part = partition(gatherer.langfiles, lambda e : (e["repo"], e["mod_name"], e["lang"]))
    symi_part = partition(gatherer.symis, lambda e : (e["repo"], e["mod_name"], e["name"]))
    defi_part = partition(gatherer.defis, lambda e : (e["repo"], e["mod_name"], e["name"], e["lang"]))

    symi_part2 = partition(gatherer.symis, lambda e : (e["repo"], e["mod_name"]))


    # Check that for every language file there is a corresponding signature file
    if verbosity >= 1:
        for langf in gatherer.langfiles:
            k = (langf["repo"], langf["mod_name"])
            if k not in sigf_part:
                print(f"{langf['path']}: No signature file with name '{langf['mod_name']}' found in repo '{langf['repo']}'.")
                print("   Signature files for the following modules were found in the repo:", 
                        ", ".join(unique_list([e[1] for e in sigf_part.keys() if e[0] == langf["mod_name"]])))
                continue
            sigfiles = sigf_part[k]
            sigf = sigfiles[0]
            if {"mhmodnl" : "modsig", "gviewnl" : "gviewsig" }[langf["type"]] != sigf["type"]:
                print(f"{langf['path']}: Is of type {langf['type']} but the signature file ({sigf['path']}) is {sigf['type']}")


    # Check that for every language file there is a corresponding signature file
    if verbosity >= 1:
        for langfk in langf_part:
            langfs = langf_part[langfk]
            if len(langfs) > 1:
                print(f"Multiple files for '{langfs[0]['mod_name']}' in repo '{langfs[0]['repo']}' for '{langfs[0]['lang']}':")
                for langf in langfs:
                    print(f"    {langf['path']}")
        for sigfk in sigf_part:
            sigfs = sigf_part[sigfk]
            if len(sigfs) > 1:
                print(f"Multiple signature files for '{sigfs[0]['mod_name']}' in repo '{sigfs[0]['repo']}':")
                for sigf in sigfs:
                    print(f"    {sigf['path']}")

    # Check that for every defi there is a symi
    if verbosity >= 2:
        for defik in defi_part:
            defi = defi_part[defik][0]  # we don't care about different verbalizations
            k = (defi["repo"], defi["mod_name"], defi["name"])
            if k not in symi_part:
                print(f"{defi['path']} at {defi['offset']}: Symbol '{defi['name']}' not found in signature file")
                k2 = (defi["repo"], defi["mod_name"])
                if k2 in symi_part2:
                    print("    The following symbols were found in the signature file:",
                        ", ".join(unique_list([e["name"] for e in symi_part2[k2]])))
                else:
                    print("    No symbols were found in the signature file")

    # Check that every verbalization is introduced only once
    if verbosity >= 2:
        for defik in defi_part:
            defis = defi_part[defik]
            part = partition(defis, lambda e : e["string"])
            for verbalization in part:
                vs = part[verbalization]
                if len(vs) > 1:
                    print("Verbalization '{verbalization}' provided multiple times:")
                    for v in vs:
                        print(f"    {v['path']} at {v['offset']}")

    # Check if symbol was introduced several times with symi
    if verbosity >= 2:
        for symik in symi_part:
            symis = [s for s in symi_part[symik] if s["type"] == "symi"]
            if len(symis) > 1:
                print(f"Symbol '{symis[0]['name']}' was introduced several times in a symi:")
                for symi in symis:
                    print(f"    {symi['path']} at {symi['offset']}")

def check_mvx(gatherer):
    langf_part = partition(gatherer.langfiles, lambda e : (e["repo"], e["mod_name"], e["lang"]))
    symi_part = partition(gatherer.symis, lambda e : (e["repo"], e["mod_name"]))
    defi_part = partition(gatherer.defis, lambda e : (e["repo"], e["mod_name"], e["name"], e["lang"]))

    for langfk in langf_part:
        if (langfk[0], langfk[1]) not in symi_part:  # no symbols introduced
            continue
        required_symbols = [e["name"] for e in symi_part[(langfk[0], langfk[1])]]
        missing_symbols = [s for s in required_symbols if (langfk[0], langfk[1], s, langfk[2]) not in defi_part]
        langf = langf_part[langfk][0]
        if len(missing_symbols) > 0:
            print(f"{langf['path']}: Missing verbalizations for the following symbols: {', '.join(unique_list(missing_symbols))}")

def check_mvlang(gatherer, lang):
    sigf_part = partition(gatherer.sigfiles, lambda e : (e["repo"], e["mod_name"]))
    langf_part = partition(gatherer.langfiles, lambda e : (e["repo"], e["mod_name"], e["lang"]))
    symi_part = partition(gatherer.symis, lambda e : (e["repo"], e["mod_name"]))
    defi_part = partition(gatherer.defis, lambda e : (e["repo"], e["mod_name"], e["name"], e["lang"]))

    for (repo, modname) in symi_part:
        if (repo, modname, lang) not in langf_part:
            print(f"{sigf_part[(repo, modname)][0]['path']}: No mhmodnl for language '{lang}'")
            continue
        langf = langf_part[(repo, modname, lang)][0]
        covered = []
        for symi in symi_part[(repo, modname)]:
            if symi["name"] in covered:
                continue
            if (repo, modname, symi["name"], lang) in defi_part:
                continue
            print(f"{symi['path']} at {symi['offset']}: No verbalization for symbol '{symi['name']}' in '{langf['path']}'")
            covered.append(symi["name"])


if __name__ == "__main__":
    def print_usage():
        print("Usage:   smglom_debug.py [VERBOSITY] [OPTIONS]* {DIRECTORY}")
        print("Example: smglom_debug.py -v3 -mv-en ~/git/gl_mathhub_info/smglom")
        print()
        print("VERBOSITY    Can be -v1, -v2, and -v3 where is the highest")
        print("OPTIONS      Options are:")
        print("                 -mv-...  Show all missing verbalizations for the language '...', where ... is e.g. en or de")
        print("                 -mvx     Show verbalizations missing in existing mhmodnls")
    if len(sys.argv) < 2:
        print("Not enough arguments\n")
        print_usage()
        sys.exit(1)

    verbosity = 3
    mv_lang = []
    mvx = False
    for arg in sys.argv[1:-1]:
        if arg == "-mvx":
            mvx = True
        elif arg in ["-v1", "-v2", "-v3"]:
            verbosity = int(sys.argv[1][-1])
        elif arg.startswith("-mv-"):
            mv_lang.append(arg[4:])
        else:
            print(f"Unexpected argument '{arg}'\n")
            print_usage()
            sys.exit(1)

    if verbosity >= 2:
        print("GATHERING DATA\n")
    ctx = harvest.HarvestContext(verbosity, harvest.DataGatherer())
    harvest.gather_stats_for_all_repos(sys.argv[-1], ctx)

    if verbosity >= 2:
        print("\n\nCHECKING DATA\n")
    check_data(ctx.gatherer, verbosity)

    if mvx:
        if verbosity >= 2:
            print("\n\nLOOKING FOR MISSING VERBALIZATIONS IN MHMODNLs\n")
        check_mvx(ctx.gatherer)

    for lang in mv_lang:
        if verbosity >= 2:
            print("\n\nLOOKING FOR MISSING VERBALIZATIONS OF LANGUAGE '" + lang + "'\n")
        check_mvlang(ctx.gatherer, lang)

