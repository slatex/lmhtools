#!/usr/bin/env python3

"""
Can be used to creates statistics about smglom.

This script analyzes the data collected with smglom_harvet.py.
A verbosity level can be set to change the what kind of errors
should be displayed during data collection.
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

def print_stats(gatherer):
    repos = unique_list([e["repo"] for e in gatherer.sigfiles + gatherer.langfiles])
    langs = unique_list([e["lang"] for e in gatherer.langfiles])

    sigf_part = partition(gatherer.sigfiles, lambda e : (e["repo"]))
    langf_part = partition(gatherer.langfiles, lambda e : (e["repo"]))
    symi_part = partition(gatherer.symis, lambda e : (e["repo"]))
    defi_part = partition(gatherer.defis, lambda e : (e["repo"], e["lang"]))
    trefi_part = partition(gatherer.trefis, lambda e : e["repo"])

    print(f"{'repo':20}{'modules':>9}{'symbols':>9}{'trefis':>9}"+"".join([f"{lang:>9}" for lang in langs])+f"{'views':>9}")
    print("-"*(20+9+9+9+9+9*len(langs)))
    for repo in repos:
        suffix = ""
        if repo not in symi_part:
            symbols = 0
        else:
            symbols = len(set([(e["mod_name"], e["name"]) for e in symi_part[repo]]))
        for lang in langs:
            if (repo, lang) not in defi_part:
                verbs = 0
            else:
                verbs = len(set([(e["mod_name"], e["name"]) for e in defi_part[(repo, lang)]]))
            if symbols == 0:
                suffix += f"{'n/a':>9}"
            else:
                s = "%.1f" % (100 * verbs/symbols)
                suffix += f"{s+'%':>9}"
        modsigs = 0
        gviewsigs = 0
        if repo in sigf_part:
            modsigs = len([e for e in sigf_part[repo] if e['type']=='modsig'])
            gviewsigs = len([e for e in sigf_part[repo] if e['type']=='gviewsig'])
        trefis = 0
        if repo in trefi_part:
            trefis = len(trefi_part[repo])
        print(f"{repo:20}" +
              f"{modsigs:9}" +
              f"{symbols:9}" +
              f"{trefis:9}" +
              suffix +
              f"{gviewsigs:9}")
    
    print("-"*(20+9+9+9+9+9*len(langs)))
    suffix = ""
    symbols = len(set([(e["mod_name"], e["name"]) for e in gatherer.symis]))
    for lang in langs:
        verbs = len(set([(e["mod_name"], e["name"]) for e in gatherer.defis if e["lang"] == lang]))
        if symbols == 0:
            suffix += f"{'n/a':>9}"
        else:
            s = "%.1f" % (100 * verbs/symbols)
            suffix += f"{s+'%':>9}"
    print(f"{'TOTAL':20}" +
          f"{len([e for e in gatherer.sigfiles if e['type']=='modsig']):9}" +
          f"{symbols:9}" +
          f"{len(gatherer.trefis):9}" +
          suffix +
          f"{len([e for e in gatherer.sigfiles if e['type']=='gviewsig']):9}")

if __name__ == "__main__":
    if len(sys.argv) != 2 and (len(sys.argv) != 3 or sys.argv[1] not in ["-v0", "-v1", "-v2", "-v3", "-v4"]):
        print("Usage:   smglom_stats.py [VERBOSITY] {DIRECTORY}")
        print("Example: smglom_stats.py -v3 ~/git/gl_mathhub_info/smglom")
        print("The verbosity can be -v0, -v1, -v2, and -v3, -v4 where -v4 is the highest")
    else:
        verbosity = 1
        if len(sys.argv) == 3:
            verbosity = int(sys.argv[1][-1])

        if verbosity >= 2:
            print("GATHERING DATA\n")
        ctx = harvest.HarvestContext(verbosity, harvest.DataGatherer())
        harvest.gather_stats_for_all_repos(sys.argv[-1], ctx)

        print("\n\nSTATISTICS\n")
        print_stats(ctx.gatherer)
    

