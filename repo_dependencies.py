#!/usr/bin/env python3

"""
Script for fixing the repository dependencies in META-INF/MANIFEST.MF
"""

import os
import re
import smglom_harvest as harvest

TOKEN_MHINPUTREF = -1
TOKEN_MHGRAPHICS = -2

re_mhinputref = re.compile(
        r"\\n?mhinputref\s*"
        r"(?:\[(?P<params>[^\]]*)\])?\s*"          # parameter
        r"\{(?P<arg>" + harvest.re_arg + r")\}"    # arg
        )

re_mhgraphics = re.compile(
        r"\\mhgraphics\s*"
        r"(?:\[(?P<params>[^\]]*)\])?\s*"          # parameter
        r"\{(?P<arg>" + harvest.re_arg + r")\}"    # arg
        )

REGEXES = [
        (harvest.re_guse, harvest.TOKEN_GUSE),
        (harvest.re_gimport, harvest.TOKEN_GIMPORT),
        (harvest.re_importmhmodule, harvest.TOKEN_IMPORTMHMODULE),
        (harvest.re_usemhmodule, harvest.TOKEN_USEMHMODULE),
        (re_mhinputref, TOKEN_MHINPUTREF),
        (re_mhgraphics, TOKEN_MHGRAPHICS),
        ]

def gather_repos(path, REPOS):
    with open(path, "r") as fp:
        string = harvest.preprocess_string(fp.read())
        tokens = harvest.parse(string, REGEXES)
        for (match, token_type) in tokens:
            if token_type in [harvest.TOKEN_GUSE, harvest.TOKEN_GIMPORT, TOKEN_MHINPUTREF]:
                # repo is optional argument
                repo = match.group("params")
                if repo and repo not in REPOS.keys():
                    REPOS[repo] = f"{path}:{harvest.get_file_pos_str(string, match.start())}: {match.group(0)}"
            elif token_type in [harvest.TOKEN_IMPORTMHMODULE, harvest.TOKEN_USEMHMODULE, TOKEN_MHGRAPHICS]:
                params = harvest.get_params(match.group("params"))
                key = "repos"
                if token_type == TOKEN_MHGRAPHICS:
                    key = "mhrepos"
                if key in params.keys():
                    repo = params[key]
                    if repo and repo not in REPOS.keys():
                        REPOS[repo] = f"{path}:{harvest.get_file_pos_str(string, match.start())}: {match.group(0)}"
            else:
                assert False

def get_olddeps(line):
    line = line[len("dependencies:"):]
    while line and line[0] == " ":
        line = line[1:]
    sep = re.compile(r",\s*")
    return sep.split(line)

def adjust_manifest(dir_path, REPOS):
    new_manifest = ""
    found_deps = False
    new_line = "dependencies: " + ",".join(REPOS.keys())
    with open(os.path.join(dir_path, "../META-INF/MANIFEST.MF"), "r") as fp:
        for line in fp:
            if line.startswith("dependencies: "):
                if found_deps:
                    print("ERROR: Multiple entries for dependencies found in manifest")
                    return
                old_entries = set(get_olddeps(line[:-1]))
                new_entries = set(REPOS.keys())
                if old_entries == new_entries:
                    print("The dependencies are already up-to-date")
                    return
                if new_entries - old_entries:
                    print("Adding the following dependencies:", ",".join(list(new_entries - old_entries)))
                    print()
                if old_entries - new_entries:
                    print("Removing the following dependencies:", ",".join(list(old_entries - new_entries)))
                    print()
                print("old " + line[:-1])
                print("new " + new_line)
                new_manifest += new_line + "\n"
                found_deps = True
            else:
                new_manifest += line
    if not found_deps:
        print()
        print("No entry for dependencies found in "  + os.path.join(dir_path, "META-INF/MANIFEST.MF"))
        print("Appending the following entry:")
        print(new_line)
        new_manifest += new_line + "\n"

    print()
    i = input("Do you want to apply these changes? (enter 'y' to confirm): ")
    if i == 'y':
        with open(os.path.join(dir_path, "../META-INF/MANIFEST.MF"), "w") as fp:
            fp.write(new_manifest)
        print("Dependecies successfully updated")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Script for fixing repo dependencies in META-INF/MANIFEST.MF",
            epilog="Example call: repo_dependencies.py -v0 ../../sets")
    parser.add_argument("-v", "--verbosity", type=int, default=1, choices=range(4), help="the verbosity (default: 1)")
    parser.add_argument("DIRECTORY", nargs="+", help="git repo or higher level directory for which statistics are generated")
    args = parser.parse_args()

    if args.verbosity >= 2:
        print("GATHERING DATA\n")
    logger = harvest.SimpleLogger(args.verbosity)

    # determine mathhub folder
    mathhub_repo = os.path.abspath(args.DIRECTORY[0])
    while not mathhub_repo.endswith("MathHub"):
        new = os.path.split(mathhub_repo)[0]
        if new == mathhub_repo:
            raise Exception("Failed to infer MathHub directory")
        mathhub_repo = new

    for directory in args.DIRECTORY:
        if not os.path.isdir(os.path.join(directory, ".git")):  ## TODO: Is there a better way?
            raise Exception("'" + directory + "' doesn't appear to be a git repository")
        
        REPOS = {}   # repo name to evidence
        dir_path = os.path.join(directory, "source")
        for root, dirs, files in os.walk(dir_path):
            for file_name in files:
                if file_name.endswith(".tex"):
                    gather_repos(os.path.join(root, file_name), REPOS)
        for repo in REPOS.keys():
            print("I found this dependency:", repo)
            print("Evidence:", REPOS[repo])
        print()
        to_ignore = None
        for repo in REPOS.keys():
            rp = os.path.abspath(os.path.join(dir_path, "../../..", repo))
            if not os.path.isdir(rp):
                print("WARNING: I didn't find the directory " + rp)
            if directory.endswith(repo):
                print("WARNING: It appears that you self-reference the repo:")
                print("         " + REPOS[repo])
                print("         -> I'm going to ignore this entry")
                to_ignore = repo
        del REPOS[to_ignore]
        print()
        print()
        adjust_manifest(dir_path, REPOS)
