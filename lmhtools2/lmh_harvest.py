from lmh_logging import *
from lmh_elements import *
from lmh_referencer import Referencer
import os



class LmhContext(object):
    def __init__(self, logger, mhdir):
        self.logger = logger
        self.mhdir = os.path.realpath(os.path.abspath(mhdir))
        self.repos = []
        self.referencer = Referencer(self)

    def log(self, entry):
        self.logger.log(entry)

    def set_repos(self, repos):
        self.repos = repos

    def path_to_pos(self, path):
        ''' Transforms a path into a Position object. This requires the repos to be set. '''
        restpath = os.path.relpath(path, self.mhdir).split(os.sep)

        repo = None
        for n in range(1, len(restpath)):
            newpath = os.path.realpath(os.path.join(self.mhdir, os.sep.join(restpath[:n])))
            for r in self.repos:
                if newpath == r.path:
                    repo = r
                    restpath = restpath[n:]
            if repo:
                break
        if not repo:
            raise Exception(f'Failed to determine repo in "{path}"\nKnown repos: {" ".join([r.repo for r in self.repos])}')

        if len(restpath) == 0:
            return Position(repo=repo.repo)
        if restpath[0] == 'source':
            restpath = restpath[1:]
        else:
            return Position(repo=repo.repo, path=path)

        if len(restpath) == 0:
            raise Exception(f'Failed to determine filename in "{path}"')

        filename = restpath[-1]
        if filename.endswith('.tex'):
            filename = filename[:-4]

        dir_ = '/'.join(restpath[:-1])
        return Position(repo=repo.repo, directory=dir_, filename=filename, path=path)

    def find_repo(self, repo):
        for r in self.repos:
            if repo == r.repo:
                return r
        return None

class LmhRepo(object):
    def __init__(self, directory, ctx):
        self.ctx = ctx
        self.path = os.path.realpath(os.path.abspath(directory))
        # by default, repo name corresponds to path
        self.repo = '/'.join([e for e in os.path.relpath(directory, ctx.mhdir).split(os.sep) if e != ''])
        self.dependencies = []
        self.manifest_properties = {}
        self.position = Position(repo = self.repo)

        self.__handle_manifest()

    def __handle_manifest(self):
        path = os.path.join(self.path, 'META-INF', 'MANIFEST.MF')
        if not os.path.isfile(path):
            self.ctx.logger.log(LogEntry(LOG_WARN, 'Failed to find META-INF/MANIFEST.MF',
                self.position, E_MISSING_MANIFEST))
            return

        with open(path) as fp:
            for line in fp:
                if ':' not in line: continue
                key = line[:line.index(':')].strip()
                val = line[line.index(':')+1:].strip()
                if key in self.manifest_properties:
                    self.ctx.logger.log(LogEntry(LOG_ERROR, f'Two entries for "{key}" in {path}',
                        self.position, E_MANIFEST_ERROR))
                self.manifest_properties[key] = val

        if 'dependencies' in self.manifest_properties:
            sep = re.compile(r',\s*')
            self.dependencies.append(sep.split(self.manifest_properties['dependencies']))
        if 'id' in self.manifest_properties:
            self.repo = self.manifest_properties['id']
        else:
            self.ctx.logger.log(LogEntry(LOG_ERROR, f'Missing entry for "id" in {path}',
                self.position, E_MANIFEST_ERROR))



class Harvester(object):
    def __init__(self, logger, mhdir):
        self.logger = logger
        self.mhdir = mhdir
        self.ctx = LmhContext(self.logger, self.mhdir)

        self.repos = []
        self.files = []

        self.__collect_repos(None)
        self.ctx.set_repos(self.repos)

    skip_regex = re.compile(f'^(((localpaths)|(all))|(((all)|(glossary))\\.({LANG_REGEX})))\\.tex$')
    def __get_file_list(self, regex):
        for repo in self.repos:
            if not re.match(regex, repo.repo):
                continue
            dir_path = os.path.join(repo.path, 'source')
            for root, dirs, files in os.walk(dir_path):
                for file_name in files:
                    path = os.path.join(root, file_name)
                    if not file_name.endswith('.tex'):
                        continue

                    # len('all.zhs.tex') == 11
                    # elif file_name == 'localpaths.tex' or \
                    #        (file_name.startswith('all.') and len(file_name) < 12):
                    elif Harvester.skip_regex.match(file_name):
                        self.logger.log_skip(f'Skipping {path}', repo.position)
                        continue
                    else:
                        yield path

    def load_files(self, regex='^.*$'):
        paths = list(self.__get_file_list(regex))

        for path in paths:
            self.load_file(path)

    def load_file(self, path):
        self.files.append(LmhFile(path, self.ctx))
        self.ctx.referencer.add_file(self.files[-1])

    


    def __collect_repos(self, directory=None):
        ''' recursively finds git repos and collects them '''
        if not directory:
            directory = self.mhdir

        if os.path.isdir(os.path.join(directory, '.git')):  ## TODO: Is there a better way?
            try:
                self.repos.append(LmhRepo(directory, self.ctx))
            except Exception as ex:
                self.logger.log_fatal(f'An unexpected error occured while processing git repository {directory}:',
                        ex, Position())
            return

        for subdir in os.listdir(directory):
            if subdir.lower() == 'meta-inf':
                self.logger.log_skip(f'Skipping directory {directory}', Position())
                continue
            subdirpath = os.path.join(directory, subdir)
            if os.path.isdir(subdirpath):
                self.__collect_repos(subdirpath)

    

