from lmh_logging import *
from regexes import *
import re
import os


class Position(object):
    def __init__(self, repo=None, directory=None, filename=None, fileoffset=None, path=None):
        self.repo = repo
        self.directory = directory
        self.filename = filename
        self.fileoffset = fileoffset
        self.path = path

    def with_offset(self, offset):
        return Position(repo=self.repo, directory=self.directory,
                filename=self.filename, fileoffset=offset, path=self.path)

    def toString(self, short=False):
        offsetstr = ':' + self.fileoffset.toString() if self.fileoffset else ''
        if (not short and self.path) or not self.repo:
            return f'{self.path}{offsetstr}'
        if self.repo:
            if self.directory and self.filename:
                return f'{self.repo}/{self.directory}/{self.filename}{offsetstr}'
            elif self.directory:
                return f'{self.repo}/{self.file_name}{offsetstr}'
            return f'{self.repo}'
        return ''



class Offset(object):
    def __init__(self, index, line, col=None):
        self.index = index
        self.line = line
        self.col = col

    def toString(self):
        if self.col:
            return f'{self.line}:{self.col}'
        else:
            return f'{self.line}'


class TexNode(object):
    def __init__(self, lmhfile, parent, ctx, end_token = None):
        self.lmhfile = lmhfile
        self.parent = parent
        self.ctx = ctx
        self.children = []
        self.end_token = end_token

    def parse(self, tokens):
        i = 0
        while i < len(tokens):
            match, tt = tokens[i]
            if tt == self.end_token:
                return tokens[i+1:]

            if tt == TOKEN_DEFI:
                self.children.append(DEFI(self, match))
            elif tt == TOKEN_TREFI:
                self.children.append(TREFI(self, match))
            elif tt == TOKEN_SYMI:
                self.children.append(SYMI(self, match))
            elif tt == TOKEN_SYMDEF:
                self.children.append(SYMDEF(self, match))
            elif tt == TOKEN_IMPORTMHMODULE:
                self.children.append(IMPORTMHMODULE(self, match))
            elif tt == TOKEN_USEMHMODULE:
                self.children.append(USEMHMODULE(self, match))
            elif tt == TOKEN_GIMPORT:
                self.children.append(GIMPORT(self, match))
            elif tt == TOKEN_GUSE:
                self.children.append(GUSE(self, match))
            elif tt == TOKEN_MHINPUTREF:
                self.children.append(MHINPUTREF(self, match))

            elif tt == TOKEN_BEGIN_MODULE:
                self.children.append(MODULE(self, match))
            elif tt == TOKEN_BEGIN_MODSIG:
                self.children.append(MODSIG(self, match))
            elif tt == TOKEN_BEGIN_MHMODNL:
                self.children.append(MHMODNL(self, match))
            elif tt == TOKEN_BEGIN_GVIEWSIG:
                self.children.append(GVIEWSIG(self, match))
            elif tt == TOKEN_BEGIN_GVIEWNL:
                self.children.append(GVIEWNL(self, match))

            elif tt in ENV_END_TOKENS:
                self.ctx.log(LogEntry(LOG_ERROR, f'Unexpected environment end: {match.group(0)}',
                    self.lmhfile.get_position(match.start()), E_STEX_PARSE_ERROR))
                return []

            if tt in ENV_BEGIN_TOKENS:
                tokens = self.children[-1].parse(tokens[i+1:])
                i = 0
            else:
                i += 1
        if self.end_token:
            self.ctx.log(LogEntry(LOG_ERROR, f'Environment started but not closed: {self.match.group(0)}',
                self.position, E_STEX_PARSE_ERROR))
        return []

    def collect_children(self, collect, skip = []):
        for c in skip:
            if isinstance(self, c):
                return []

        for c in collect:
            if isinstance(self, c):
                return [self]

        l = []
        for c in self.children:
            l += c.collect_children(collect, skip)
        return l

    def get_parent(self, goal=None, goals=[]):
        assert not goal and goals
        if goal:
            goals = [goal]
        for goal in goals:
            if isinstance(self, goal):
                return self
        if not self.parent:
            return None
        return self.parent.get_parent(goals = goals)



# MACROS

class LmhMacro(TexNode):
    def __init__(self, parent, match):
        TexNode.__init__(self, parent.lmhfile, parent, parent.ctx)
        self.match = match
        self.position = self.lmhfile.get_position(self.match.start())

class DEFI(LmhMacro):
    def __init__(self, parent, match):
        LmhMacro.__init__(self, parent, match)
        self.params = get_params(match.group('params'))
        args, other_arg = get_args(match, False, self.ctx, self.position)
        self.symb = self.params['name'] if 'name' in self.params else '-'.join(args)
        self.display = other_arg if other_arg else ' '.join(args)
        if match.group('start')[0] == 'D':
            self.display = self.display.capitalize()
        if match.group('plurals'):
            self.display += 's'
        self.lang = None
        p = self.get_parent(goals=[MHMODNL, MODULE, GVIEWNL])
        if p:
            self.lang = p.lang
        self.symbol = None     # set by referencer

class TREFI(LmhMacro):
    def __init__(self, parent, match):
        LmhMacro.__init__(self, parent, match)
        params = match.group('params')
        args, other_arg = get_args(match, False, self.ctx, self.position)
        if match.group('start')[0] != 'a':
            assert not other_arg
            self.display = ' '.join(args)
        else:
            self.ctx.log(LogEntry(LOG_ERROR, f'Use of atrefi is deprecated (and may result in errors)',
                self.position, E_STEX_PARSE_ERROR))
            self.display = other_arg
        if match.group('start').isupper():
            self.display = self.display.capitalize()
        if match.group('plurals'):
            self.display += 's'
        self.isdrefi = 'd' in match.group('start')[0].lower()

        self.target_mod = None
        self.symb = '-'.join(args)
        # with params, the defaults can be changed
        if params:
            self.target_mod = params
            if '?' in params:
                self.target_mod = params.split('?')[0]
                self.symb = params.split('?')[1]
                if not match.group('start').lower()[0] in ['m', 'd']:
                    self.ctx.log(LogEntry(LOG_ERROR, f'Expected trefi or drefi for "{match.group()}"',
                        self.position, E_STEX_PARSE_ERROR))
        if not self.target_mod:
            # by default, target module is is current module
            self.target_mod = self.position.filename
            parent = self.get_parent(goals=[MODULE, MHMODNL])
            if parent:
                self.target_mod = parent.mod
        self.symbol = None     # set by referencer


class SYMI(LmhMacro):
    def __init__(self, parent, match):
        LmhMacro.__init__(self, parent, match)
        args, other_arg = get_args(match, True, self.ctx, self.position)
        assert not other_arg
        self.symb = '-'.join(args)
        self.params = get_params(match.group('params'))
        self.symbol = None     # set by referencer

class SYMDEF(LmhMacro):
    def __init__(self, parent, match):
        LmhMacro.__init__(self, parent, match)
        self.params = get_params(match.group('params'))
        self.symb = self.params['name'] if 'name' in self.params else match.group('arg0')
        self.symbol = None     # set by referencer

class IMPORTMHMODULE(LmhMacro):
    def __init__(self, parent, match):
        LmhMacro.__init__(self, parent, match)
        self.params = get_params(match.group('params'))

        repo = self.position.repo.repo
        if 'repos' in self.params:
            self.ctx.log(LogEntry(LOG_WARN, f'"repos" is deprecated - use "mhrepos" instead',
                self.position, E_STEX_PARSE_ERROR))
            repo = self.params['repos']
        if 'mhrepos' in self.params:
            repo = self.params['mhrepos']
        dir_ = None
        path = None
        mod = match.group('arg')
        if 'dir' in self.params:
            dir_ = self.params['dir']
        r = self.ctx.find_repo(repo)
        if not r:
            self.ctx.log(LogEntry(LOG_ERROR, f'Failed to find repo "{repo}" for "{match.group(0)}"',
                self.position, E_STEX_PARSE_ERROR))
        if r and 'path' in self.params:
            path = os.path.join(r.path, 'source', self.params['path'], mod + '.tex')
        self.target_position = Position(repo=r, directory=dir_, filename=mod, path=path)
        self.target_file = None


class USEMHMODULE(LmhMacro):
    def __init__(self, parent, match):
        LmhMacro.__init__(self, parent, match)

        self.params = get_params(match.group('params'))
        repo = self.position.repo.repo
        if 'repos' in self.params:
            self.ctx.log(LogEntry(LOG_WARN, f'"repos" is deprecated - use "mhrepos" instead',
                self.position, E_STEX_PARSE_ERROR))
            repo = self.params['repos']
        if 'mhrepos' in self.params:
            repo = self.params['mhrepos']
        dir_ = None
        path = None
        mod = match.group('arg')
        if 'dir' in self.params:
            dir_ = self.params['dir']
        r = self.ctx.find_repo(repo)
        if not r:
            self.ctx.log(LogEntry(LOG_ERROR, f'Failed to find repo "{repo}" for "{match.group(0)}"',
                self.position, E_STEX_PARSE_ERROR))
        if r and 'path' in self.params:
            path = os.path.join(r.path, 'source', self.params['path'], mod + '.tex')
        self.target_position = Position(repo=r, directory=dir_, filename=mod, path=path)
        self.target_file = None

class MHINPUTREF(LmhMacro):
    def __init__(self, parent, match):
        LmhMacro.__init__(self, parent, match)

        repo = self.position.repo
        params = match.group('params')
        if params:
            repo = params
        a = match.group('arg')
        filename = a.split('/')[-1]
        dir_ = a.split('/')[:-1]
        self.target_position = Position(repo=repo, filename=filename, directory = dir_ if dir_ else None)
        self.target_file = None

class GIMPORT(LmhMacro):
    def __init__(self, parent, match):
        LmhMacro.__init__(self, parent, match)

        self.target_repo = match.group('params')
        if not self.target_repo:
            self.target_repo = self.position.repo
        self.target_mod = match.group('arg')
        self.target_position = Position(repo=self.target_repo, filename=self.target_mod, directory=None)
        self.target_file = None

class GUSE(LmhMacro):
    def __init__(self, parent, match):
        LmhMacro.__init__(self, parent, match)

        self.target_repo = match.group('params')
        if not self.target_repo:
            self.target_repo = self.position.repo
        self.target_mod = match.group('arg')
        self.target_position = Position(repo=self.target_repo, filename=self.target_mod, directory=None)
        self.target_file = None


# ENVIRONMENTS

class LmhEnvironment(TexNode):
    def __init__(self, parent, match, end_token):
        TexNode.__init__(self, parent.lmhfile, parent, parent.ctx, end_token)
        self.position = self.lmhfile.get_position(match.start())

class MODULE(LmhEnvironment):
    def __init__(self, parent, match):
        LmhEnvironment.__init__(self, parent, match, TOKEN_END_MODULE)

        self.params = get_params(match.group('params'))
        if 'id' in self.params:
            self.mod = self.params['id']
        else:
            self.mod = self.position.filename
            self.ctx.log(LogEntry(LOG_ERROR, f'Module doesn\'t have "id" parameter', self.position,
                E_STEX_PARSE_ERROR))
        self.lang = 'mono'

class MODSIG(LmhEnvironment):
    def __init__(self, parent, match):
        LmhEnvironment.__init__(self, parent, match, TOKEN_END_MODSIG)
        self.mod = match.group('name')
        self.params = get_params(match.group('params'))


class MHMODNL(LmhEnvironment):
    def __init__(self, parent, match):
        LmhEnvironment.__init__(self, parent, match, TOKEN_END_MHMODNL)
        self.lang = match.group('lang')
        self.mod = match.group('name')

class GVIEWSIG(LmhEnvironment):
    def __init__(self, parent, match):
        LmhEnvironment.__init__(self, parent, match, TOKEN_END_GVIEWSIG)
        self.mod = match.group('name')

class GVIEWNL(LmhEnvironment):
    def __init__(self, parent, match):
        LmhEnvironment.__init__(self, parent, match, TOKEN_END_GVIEWNL)
        self.lang = match.group('lang')
        self.mod = match.group('name')

# FILES

class LmhFile(TexNode):
    def __init__(self, path, ctx):
        TexNode.__init__(self, self, None, ctx)
        self.path = path
        self.position = ctx.path_to_pos(path)
        with open(path, 'r') as fp:
            self.string = fp.read()
        self.__preprocess_string()
        self.__generate_offset_map()

        self.parse(tokenize(self.string, REGEXES))
        self.declared_symbols = []

#         self.__determine_filetype()
# 
#     def __determine_filetype(self):
#         self.filetype = 'unknown'
# 
#         if len(self.children) == 1:
#             c = self.children[0]
#             if isinstance(c, MODULE):
#                 self.filetype = 'module'
#             elif isinstance(c, MODSIG):
#                 self.filetype = 'modsig'
#             elif isinstance(c, MHMODNL):
#                 self.filetype = 'mhmodnl'
#             elif isinstance(c, GVIEWSIG):
#                 self.filetype = 'gviewsig'
#             elif isinstance(c, GVIEWNL):
#                 self.filetype = 'gviewnl'
#             # elif isinstance(c, OMGROUP):
#             #     self.filetype = 'omgroup'
#         elif len(self.children) == 0:
#             self.filetype = 'empty'   # no relevant stex


    commentregex = re.compile('(^|\n)[\t ]*\%[^\n]*\n')
    def __preprocess_string(self):
        ''' removes comment lines, but keeps linebreaks to maintain line numbers
            TODO: Implement this in a cleaner way!
        '''
        s = LmhFile.commentregex.sub('\\1\n', self.string)
        while s != self.string:
            self.string = s
            s = LmhFile.commentregex.sub('\\1\n', self.string)

    def __generate_offset_map(self):
        self.offset_map = []
        linenumber = 1
        charnumber = 1
        for c in self.string:
            self.offset_map.append((linenumber, charnumber))
            if c == "\n":
                linenumber += 1
                charnumber = 1
            else:
                charnumber += 1

    def __get_offset(self, index):
        entry = self.offset_map[index]
        return Offset(index=index, line=entry[0], col=entry[1])

    def get_position(self, index):
        offset = self.__get_offset(index)
        return self.position.with_offset(offset)







