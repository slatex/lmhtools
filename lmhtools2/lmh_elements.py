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
                self.ctx.logger.log(LogEntry(LOG_ERROR, f'Unexpected environment end: {match.group(0)}',
                    self.lmhfile.get_position(match.start()), E_STEX_PARSE_ERROR))
                return []

            if tt in ENV_BEGIN_TOKENS:
                tokens = self.children[-1].parse(tokens[i+1:])
                i = 0
            else:
                i += 1
        if self.end_token:
            self.ctx.logger.log(LogEntry(LOG_ERROR, f'Environment started but not closed: {self.match.group(0)}',
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



# MACROS

class LmhMacro(TexNode):
    def __init__(self, parent, match):
        TexNode.__init__(self, parent.lmhfile, parent, parent.ctx)
        self.match = match
        self.position = self.lmhfile.get_position(self.match.start())

class DEFI(LmhMacro):
    def __init__(self, parent, match):
        LmhMacro.__init__(self, parent, match)

class TREFI(LmhMacro):
    def __init__(self, parent, match):
        LmhMacro.__init__(self, parent, match)

class SYMI(LmhMacro):
    def __init__(self, parent, match):
        LmhMacro.__init__(self, parent, match)

class SYMDEF(LmhMacro):
    def __init__(self, parent, match):
        LmhMacro.__init__(self, parent, match)

class IMPORTMHMODULE(LmhMacro):
    def __init__(self, parent, match):
        LmhMacro.__init__(self, parent, match)

class USEMHMODULE(LmhMacro):
    def __init__(self, parent, match):
        LmhMacro.__init__(self, parent, match)

class GIMPORT(LmhMacro):
    def __init__(self, parent, match):
        LmhMacro.__init__(self, parent, match)

class GUSE(LmhMacro):
    def __init__(self, parent, match):
        LmhMacro.__init__(self, parent, match)

class MHINPUTREF(LmhMacro):
    def __init__(self, parent, match):
        LmhMacro.__init__(self, parent, match)


# ENVIRONMENTS

class LmhEnvironment(TexNode):
    def __init__(self, parent, match, end_token):
        TexNode.__init__(self, parent.lmhfile, parent, parent.ctx, end_token)
        self.position = self.lmhfile.get_position(match.start())

class MODULE(LmhEnvironment):
    def __init__(self, parent, match):
        LmhEnvironment.__init__(self, parent, match, TOKEN_END_MODULE)

class MODSIG(LmhEnvironment):
    def __init__(self, parent, match):
        LmhEnvironment.__init__(self, parent, match, TOKEN_END_MODSIG)

class MHMODNL(LmhEnvironment):
    def __init__(self, parent, match):
        LmhEnvironment.__init__(self, parent, match, TOKEN_END_MHMODNL)

class GVIEWSIG(LmhEnvironment):
    def __init__(self, parent, match):
        LmhEnvironment.__init__(self, parent, match, TOKEN_END_GVIEWSIG)

class GVIEWNL(LmhEnvironment):
    def __init__(self, parent, match):
        LmhEnvironment.__init__(self, parent, match, TOKEN_END_GVIEWNL)


# FILES

class LmhFile(TexNode):
    def __init__(self, path, ctx):
        TexNode.__init__(self, self, None, ctx)
        self.path = path
        self.pos = ctx.path_to_pos(path)
        with open(path, 'r') as fp:
            self.string = fp.read()
        self.__preprocess_string()
        self.__generate_offset_map()

        self.parse(tokenize(self.string, REGEXES))



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
        return self.pos.with_offset(offset)







