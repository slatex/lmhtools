import lmh_harvest as harvest
import os
import sys
import shutil

FILE = sys.argv[-1]
if not FILE.endswith('.tex'):
    print('Expected `.tex` file as an argument')
    sys.exit(1)

MATHHUB = os.path.realpath(os.getenv('MATHHUB'))
# TODO: Use argparse
if '--mathhub' in sys.argv[:-1]:
    MATHHUB = sys.argv[sys.argv.index('--mathhub')+1]
if not MATHHUB:
    print('MATHHUB is not set')
    sys.exit(1)

if not os.path.isdir(MATHHUB):
    print(f'{MATHHUB} is not a valid directory')
    sys.exit(1)

TARGET = os.path.realpath('minimathhub')
if os.path.isdir(TARGET):
    print(f'{TARGET} already exists')
    sys.exit(1)
os.mkdir(TARGET)

# STEP 1: Get archives

def getArchives(directory, archives):
    if os.path.isdir(os.path.join(directory, ".git")):  ## TODO: Is there a better way?
        mf = os.path.join(directory, 'META-INF', 'MANIFEST.MF')
        if os.path.isfile(mf):
            with open(mf, 'r') as fp:
                k = None
                for line in fp:
                    if line.startswith('id: '):
                        k = line.strip().split(' ')[1]
                        break
                if k:
                    archives[k] = os.path.realpath(directory)
        else:
            archives[os.path.relpath(directory, MATHHUB)] = os.path.realpath(directory)

    for subdir in os.listdir(directory):
        if subdir == "meta-inf":
            continue
        subdirpath = os.path.join(directory, subdir)
        if os.path.isdir(subdirpath):
            getArchives(subdirpath, archives)

ARCHIVES = {}
getArchives(MATHHUB, ARCHIVES)
ARCHIVES_INV = {p:a for (a,p) in ARCHIVES.items()}


def getArchive(path, maxups = 30):
    for i in range(maxups):
        path = os.path.realpath(path)
        if path in ARCHIVES_INV:
            return ARCHIVES_INV[path]
        newpath = os.path.join(path, os.pardir)
        # TODO: properly check for root and eliminate maxups
        if path == newpath:
            return None
        path = newpath
    return None


# STEP 2: Determine required files
USED_FILES = set()

tobeprocessed = { FILE }

while tobeprocessed:
    USED_FILES |= tobeprocessed
    tobeprocessednext = set()
    for f in tobeprocessed:
        if not os.path.isfile(f):
            print(f'Warning: can\'t find file {f}')
            continue
        with open(f, 'r') as fp:
            s = fp.read()
        s = harvest.preprocess_string(s)
        for (match, token_type) in harvest.parse(s, harvest.regexes):
            # if token_type == harvest.TOKEN_IMPORTMHMODULE:
            if token_type in {harvest.TOKEN_IMPORTMHMODULE, harvest.TOKEN_USEMHMODULE, harvest.TOKEN_MHINPUTREF}:
                params = harvest.get_params(match.group("params"))
                archive = getArchive(f)
                if "repos" in params:
                    print(f"Warning: Use of parameter 'repos' is deprecated -- use mhrepos instead. (file: {f})")
                    archive = params["repos"]
                if "mhrepos" in params:
                    archive = params["mhrepos"]
                file_name = match.group("arg") + ".tex"
                if token_type == harvest.TOKEN_MHINPUTREF and match.group("params"):
                    archive = match.group("params")
                if archive in ARCHIVES:
                    repo = ARCHIVES[archive]
                else:
                    repo = None
                    if archive:
                        print(f'Warning: Failed to find archive {archive}. (file: {f})')
                if repo and token_type == harvest.TOKEN_MHINPUTREF:
                    path = os.path.join(repo, "source", file_name)
                elif repo and "path" in params:
                    path = os.path.join(repo, "source", params["path"]) + ".tex"
                elif repo and "dir" in params:
                    path = os.path.join(repo, "source", params["dir"], file_name)
                else:
                    path = os.path.join(os.path.split(f)[0], file_name)

                path = os.path.realpath(path)
                if path in USED_FILES:
                    continue
                else:
                    tobeprocessednext.add(path)
            elif token_type in {harvest.TOKEN_GUSE, harvest.TOKEN_GIMPORT}:
                archive = getArchive(f)
                repo_param = match.group("params")
                if repo_param:
                    archive = repo_param
                mod_name = match.group("arg")
                if not archive in ARCHIVES:
                    print(f'Warning: Failed to find archive {archive}. (file: {f})')
                    continue
                repo = ARCHIVES[archive]
                path = os.path.realpath(os.path.join(repo, 'source', mod_name + '.tex'))
                if path in USED_FILES:
                    continue
                else:
                    tobeprocessednext.add(path)


    tobeprocessed = tobeprocessednext


FILE_TO_ARCHIVE = {f : getArchive(f) for f in USED_FILES}
USED_ARCHIVES = set(FILE_TO_ARCHIVE.values()) - {None}


m = lambda *x : os.path.join(MATHHUB, *x)
t = lambda *x : os.path.join(TARGET, *x)

# COPY REQUIRED ARCHIVES
for archive in USED_ARCHIVES:
    r = os.path.relpath(ARCHIVES[archive], MATHHUB).split(os.path.sep)
    for i in range(len(r)):
        rr = os.path.sep.join(r[:i+1])
        if not os.path.isdir(t(rr)):
            os.mkdir(t(rr))
            if os.path.isdir(m(rr, 'meta-inf')):
                shutil.copytree(m(rr, 'meta-inf'), t(rr, 'meta-inf'))

    rr = os.path.sep.join(r[:i+1])
    if os.path.isdir(m(rr, 'META-INF')) and not os.path.isdir(t(rr, 'META-INF')):  # otherwise problems on case-insensitive file systems (as 'meta-inf' gets copied)
        shutil.copytree(m(rr, 'META-INF'), t(rr, 'META-INF'))

# COPY REQUIRED FILES
for f in USED_FILES:
    r = os.path.relpath(f, MATHHUB).split(os.path.sep)
    for i in range(len(r[:-1])):
        rr = os.path.sep.join(r[:i+1])
        if not os.path.isdir(t(rr)):
            os.mkdir(t(rr))
    rr = os.path.sep.join(r)
    shutil.copy(os.path.join(MATHHUB, rr), os.path.join(TARGET, rr))

