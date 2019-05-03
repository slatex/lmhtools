#!/usr/bin/env python3

"""
Can be used to find certain kinds of errors in sTeX files in MathHub.

This script analyzes the data collected with lmh_harvest.py
and checks that the data is 'consistent', meaning that
for example every symbol has been introduced in a signature file.
The verbosity level changes what kind of errors are displayed.
"""

import os
import lmh_harvest as harvest

class EmacsLogger(object):
    def __init__(self, verbosity, path):
        assert 0 <= verbosity <= 4
        self.verbosity = verbosity
        self.fp = open(path, "w")
        self.something_was_logged = False

    def format_filepos(self, path, offset=None, with_col=False):
        # with_col ignored (for emacs we always need it)
        return f"{os.path.abspath(path)}:{offset if offset else 1}:"

    def log(self, message, minverbosity=1, filepath=None, offset=None):
        if self.verbosity < minverbosity:
            return False
        
        if filepath:
            self.fp.write(f"{self.format_filepos(filepath, offset, True)} {message}\n\n")
        else:
            self.fp.write(f"{message}\n\n")

        self.something_was_logged = True
        return True

    def finish(self):
        self.fp.close()


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


def check_data(gatherer, verbosity, logger):
    """
        Checks data for errors (but not for things like missing verbalizations)
        `verbosity` is needed for optimization (don't look for errors that wouldn't be logged)
    """

    # partition data for efficient look-up
    repo_part = partition(gatherer.repos, lambda e : e["repo"])
    sigf_part = partition(gatherer.sigfiles, lambda e : (e["repo"], e["mod_name"]))
    langf_part = partition(gatherer.langfiles, lambda e : (e["repo"], e["mod_name"], e["lang"]))
    symi_part = partition(gatherer.symis, lambda e : (e["repo"], e["mod_name"], e["name"]))
    defi_part = partition(gatherer.defis, lambda e : (e["repo"], e["mod_name"], e["name"], e["lang"]))

    symi_part2 = partition(gatherer.symis, lambda e : (e["repo"], e["mod_name"]))
    sigf_part2 = partition(gatherer.sigfiles, lambda e : e["repo"])


    # Check that for every language file there is a corresponding signature file
    if verbosity >= 1:
        for langf in gatherer.langfiles:
            k = (langf["repo"], langf["mod_name"])
            if k not in sigf_part:
                logger.log(f"No signature file with name '{langf['mod_name']}' found in repo '{langf['repo']}'.\n" +
                        "   Signature files for the following modules were found in the repo:\n   " +
                        ", ".join(unique_list([e[1] for e in sigf_part.keys() if e[0] == langf["mod_name"]])),
                        minverbosity=1, filepath=langf['path'])
                continue
            sigfiles = sigf_part[k]
            sigf = sigfiles[0]
            if {"mhmodnl" : "modsig", "gviewnl" : "gviewsig" }[langf["type"]] != sigf["type"]:
                logger.log(f"Is of type {langf['type']} but the signature file ({sigf['path']}) is {sigf['type']}",
                        minverbosity=1, filepath=langf['path'])


    # Check that for every language file there is a corresponding signature file
    if verbosity >= 1:
        for langfk in langf_part:
            langfs = langf_part[langfk]
            if len(langfs) > 1:
                logger.log(f"Multiple files for '{langfs[0]['mod_name']}' in repo '{langfs[0]['repo']}' for '{langfs[0]['lang']}':" +
                        "".join(["\n    " + logger.format_filepos(langf['path']) for langf in langfs]), minverbosity=1)
        for sigfk in sigf_part:
            sigfs = sigf_part[sigfk]
            if len(sigfs) > 1:
                logger.log(f"Multiple signature files for '{sigfs[0]['mod_name']}' in repo '{sigfs[0]['repo']}':" +
                        "".join(["\n    " + logger.format_filepos(sigf['path']) for sigf in sigfs]), minverbosity=1)

    # Check that for every defi there is a symi
    if verbosity >= 2:
        for defik in defi_part:
            defi = defi_part[defik][0]  # we don't care about different verbalizations
            k = (defi["repo"], defi["mod_name"], defi["name"])
            if k not in symi_part:
                message = f"Symbol '{defi['name']}' not found in signature file"
                k2 = (defi["repo"], defi["mod_name"])
                if k2 in symi_part2:
                    message += "\n    The following symbols were found in the signature file: " +\
                        ", ".join(unique_list([e["name"] for e in symi_part2[k2]]))
                else:
                    message  += "\n    No symbols were found in the signature file"
                logger.log(message, minverbosity=2, filepath=defi['path'], offset=defi['offset'])
            else:
                for symi in symi_part[k]:
                    if symi["noverb"] == "all" or defi["lang"] in symi["noverb"]:
                        logger.log(f"Symbol '{defi['name']}' has a verbalization, which conflicts with"
                              f"\n    {logger.format_filepos(symi['path'], symi['offset'], True)} noverb={repr(symi['noverb'])}",
                              minverbosity=2, filepath=defi['path'], offset=defi['offset'])


    # Check that every verbalization is introduced only once
    if verbosity >= 2:
        for defik in defi_part:
            defis = defi_part[defik]
            part = partition(defis, lambda e : e["string"])
            for verbalization in part:
                vs = part[verbalization]
                if len(vs) > 1:
                    logger.log(f"Verbalization '{verbalization}' provided multiple times:" +
                            "".join(["\n    " + logger.format_filepos(v['path'], v['offset']) for v in vs]),
                            minverbosity = 2)

    # Check if symbol was introduced several times with symi
    if verbosity >= 2:
        for symik in symi_part:
            symis = [s for s in symi_part[symik] if s["type"] == "symi" and not s["implicit"] ]
            if len(symis) > 1:
                logger.log(f"Symbol '{symis[0]['name']}' was introduced several times in a symi:" +
                        "".join(["\n    " + logger.format_filepos(symi['path'], symi['offset']) for symi in symis]),
                        minverbosity = 2)

    # Check for missing namespaces
    if verbosity >= 2:
        for repo in sigf_part2:
            if repo_part[repo][0]["namespace"]:
                continue
            for sigf in sigf_part2[repo]:
                if sigf["type"] == "modsig" and sigf["align"] and sigf["align"] != "noalign":
                    logger.log(f"Has alignment, but no namespace is set for the repository", minverbosity=2, filepath=sigf['path'])
                    break

    # Check for missing module alignments
    if verbosity >= 2:
        for sigfk in sigf_part:
            if sigf_part[sigfk][0]["type"] != "modsig" or (sigf_part[sigfk][0]["align"] and sigf_part[sigfk][0]["align"] != "noalign"):
                continue # module is aligned/doesn't need to be aligned
            
            if sigfk not in symi_part2:
                continue # no symbols - module alignment not necessary

            for symi in symi_part2[sigfk]:
                if symi["align"] and symi["align"] != "noalign":
                    logger.log(f"Found alignment, but module is not aligned",
                            minverbosity = 2, filepath=symi['path'], offset=symi['offset'])
                    break


def check_mvx(gatherer, logger):
    langf_part = partition(gatherer.langfiles, lambda e : (e["repo"], e["mod_name"], e["lang"]))
    symi_part = partition(gatherer.symis, lambda e : (e["repo"], e["mod_name"]))
    defi_part = partition(gatherer.defis, lambda e : (e["repo"], e["mod_name"], e["name"], e["lang"]))

    for langfk in langf_part:
        if (langfk[0], langfk[1]) not in symi_part:  # no symbols introduced
            continue
        required_symbols = [e["name"] for e in symi_part[(langfk[0], langfk[1])] if e["noverb"] != "all" and langfk[2] not in e["noverb"]]
        missing_symbols = [s for s in required_symbols if (langfk[0], langfk[1], s, langfk[2]) not in defi_part]
        langf = langf_part[langfk][0]
        if len(missing_symbols) > 0:
            logger.log(f"Missing verbalizations for the following symbols: {', '.join(unique_list(missing_symbols))}",
                    filepath=langf['path'])

def check_mvlang(gatherer, lang, logger):
    sigf_part = partition(gatherer.sigfiles, lambda e : (e["repo"], e["mod_name"]))
    langf_part = partition(gatherer.langfiles, lambda e : (e["repo"], e["mod_name"], e["lang"]))
    symi_part = partition(gatherer.symis, lambda e : (e["repo"], e["mod_name"]))
    defi_part = partition(gatherer.defis, lambda e : (e["repo"], e["mod_name"], e["name"], e["lang"]))

    for (repo, modname) in symi_part:
        if (repo, modname, lang) not in langf_part:
            logger.log(f"No mhmodnl for language '{lang}'", filepath=sigf_part[(repo, modname)][0]['path'])
            continue
        langf = langf_part[(repo, modname, lang)][0]
        covered = []
        for symi in symi_part[(repo, modname)]:
            if symi["name"] in covered:
                continue
            if (repo, modname, symi["name"], lang) in defi_part:
                continue
            if symi["noverb"] == "all" or lang in symi["noverb"]:
                continue
            logger.log(f"No verbalization for symbol '{symi['name']}' in file\n    {logger.format_filepos(langf['path'])}",
                    filepath=symi['path'], offset=symi['offset'])
            covered.append(symi["name"])

def check_ma(gatherer, logger):
    sigf_part = partition(gatherer.sigfiles, lambda e : e["repo"])
    symi_part = partition(gatherer.symis, lambda e : (e["repo"], e["mod_name"]))
    for repo in gatherer.repos:
        if not repo["namespace"]:
            logger.log(f"Repository '{repo['repo']}' has no namespace set in preamble")
            continue
        for sigf in sigf_part[repo['repo']]:
            if sigf["type"] == "glviewsig":
                continue
            if not sigf["align"]:
                logger.log("No module alignment provided", filepath=sigf['path'])
                continue
            for symi in symi_part[(repo["repo"], sigf["mod_name"])]:
                if not symi["align"]:
                    logger.log(f"No alignment provided for symbol {symi['name']}",
                            filepath=symi['path'], offset=symi['offset'])
            
        

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Script for finding inconsistencies in MathHub",
            epilog="Example call: smglom_debug.py -v3 -mv en de -ma ../..")
    parser.add_argument("-v", "--verbosity", type=int, default=2, choices=range(4), help="the verbosity (default: 2)")
    parser.add_argument("-ma", "--missing-alignments", action="store_true", help="show missing alignments")
    parser.add_argument("-mv", "--missing-verbalizations", type=str, metavar="LANG", nargs="*", help="show missing verbalizations for these languages(e.g. en de all)")
    parser.add_argument("-im", "--incomplete-mhmodnl", action="store_true", help="show verbalizations missing in existing mhmodnls")
    parser.add_argument("-e", "--emacs", action="store_true")
    parser.add_argument("DIRECTORY", nargs="+", help="git repo or higher level directory which is debugged")
    args = parser.parse_args()

    verbosity = args.verbosity

    if args.emacs:
        import datetime
        emacs_bufferpath = "/tmp/lmh_debug-" + str(datetime.datetime.now()).replace(" ", "T")+".log"
        logger = EmacsLogger(verbosity, emacs_bufferpath)
    else:
        logger = harvest.SimpleLogger(verbosity)

    logger.log("GATHERING DATA\n", minverbosity=2)
    mathhub_dir = harvest.get_mathhub_dir(args.DIRECTORY[0])
    ctx = harvest.HarvestContext(logger, harvest.DataGatherer(), mathhub_dir)
    for directory in args.DIRECTORY:
        harvest.gather_data_for_all_repos(directory, ctx)

    logger.log("\n\nCHECKING DATA\n", minverbosity=2)
    check_data(ctx.gatherer, verbosity, logger)

    if args.incomplete_mhmodnl:
        logger.log("\n\nLOOKING FOR MISSING VERBALIZATIONS IN MHMODNLs\n", minverbosity=2)
        check_mvx(ctx.gatherer, logger)

    mv_langs = args.missing_verbalizations
    if not mv_langs: mv_langs = []
    all_langs = sorted(list(set([e["lang"] for e in ctx.gatherer.langfiles])))
    if "all" in mv_langs:
        mv_langs = all_langs

    for lang in mv_langs:
        logger.log("\n\nLOOKING FOR MISSING VERBALIZATIONS OF LANGUAGE '" + lang + "'\n", minverbosity=2)
        if lang not in all_langs:
            logger.log(f"No files for language '{lang}' were found", minverbosity=1)
            continue
        check_mvlang(ctx.gatherer, lang, logger)

    if args.missing_alignments:
        logger.log("\n\nLOOKING FOR MISSING ALIGNMENTS\n", minverbosity=2)
        check_ma(ctx.gatherer, logger)

    if args.emacs:
        logger.finish()
        import subprocess
        subprocess.call(["emacsclient", "-a", "emacs", emacs_bufferpath])
        os.remove(emacs_bufferpath)

