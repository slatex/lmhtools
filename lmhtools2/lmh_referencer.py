from lmh_logging import *
from lmh_elements import *


class Symbol(object):
    def __init__(self, symb, repo, directory, module, declared, used=None):
        self.symb = symb
        self.repo = repo
        self.directory = directory if directory else ''
        self.module = module
        self.declared = declared
        self.used = used if used else []

    def isSame(self, symbol):
        return self.symb == symbol.symb and self.repo == symbol.repo and \
                self.directory == symbol.directory and self.module == symbol.module

    def merge(self, symbol):
        assert self.isSame(symbol)
        for d in symbol.declared:
            if d not in self.declared:
                self.declared.append(d)
        for u in self.used:
            if u not in self.used:
                self.used.append(u)


class Referencer(object):
    def __init__(self, ctx):
        self.ctx = ctx

        # (repo, dir, modname) : lmhfile
        # dir should be string (not None)
        # modname without .tex of course
        self.filemap = {}

        self.simplefilemap = {}   # simply path to file

        # string (symbol name) : list[Symbol object]
        self.symbols = {}

    def add_file(self, lmhfile):
        if self.symbols:
            raise Exception('Can\'t add new files after the symbol generation')

#         if len(lmhfile.children) == 1 and isinstance(lmhfile.children[0], MODULE):
#             nf = lmhfile.children[0].position.modname
#             if lmhfile.position.modname != nf:
#                 self.ctx.log(LogEntry(LOG_WARN, f'Filename ({lmhfile.position.modname}) does not match module name ({nf})',
#                     lmhfile.position, E_FILENAME_MISMATCH))
#                 lmhfile.position.modname = nf

        pos = lmhfile.position
        key = (pos.repo, pos.directory if pos.directory else '', pos.modname)

        if key in self.filemap:
            self.ctx.log(LogEntry(LOG_ERROR,
                f'There is already an entry for {pos.toString(True)}\n{key}  {lmhfile.position.path}  {self.filemap[key].position.path}',
                #f'There is already an entry for {pos.toString(True)}',
                pos, E_DUPLICATE_MODULE))
        else:
            self.filemap[key] = lmhfile

        if pos.path:
            if pos.path in self.simplefilemap:
                self.ctx.log(LogEntry(LOG_ERROR,
                    f'There is already an entry for {pos.path}',
                    pos, E_DUPLICATE_MODULE))
            else:
                self.simplefilemap[pos.path] = lmhfile

    

    def compile(self):
        # STEP 0: LINK TARGET FILE TO INCLUDES
        for f in self.filemap.values():
            for include in f.collect_children(collect=[USEMHMODULE, GUSE, IMPORTMHMODULE, GIMPORT, MHINPUTREF]):
                include.target_file = self.__find_file(include.target_position)

        # STEP 1: CREATE ALL INTRODUCED SYMBOLS
        for f in self.filemap.values():
            # symis and symdefs
            for sym in f.collect_children(collect=[SYMI, SYMDEF]):
                p = sym.get_parent(goals=[MODSIG, MODULE])
                if not p:
                    self.ctx.log(LogEntry(LOG_ERROR, f'"{sym.match.group(0)}" is not inside a modsig or module',
                        sym.position, E_STEX_PARSE_ERROR))
                    continue
                self.__put_symbol(Symbol(sym.symb, p.position.repo, p.position.directory, p.mod, [sym]))
            # defis
            for defi in f.collect_children(collect=[DEFI]):
                p = sym.get_parent(goals=[MODULE])
                if not p: continue   # e.g. if in mhmodnl
                self.__put_symbol(Symbol(defi.symb, p.position.repo, p.position.directory, p.mod, [defi]))

        # STEP 2: MARK DECLARED SYMBOLS IN FILES (for efficiency)
        for s in self.get_all_symbols():
            for d in s.declared:
                d.lmhfile.declared_symbols.append(s)

        # STEP 2.1: LINK MHMODNLS TO MODSIGS
        for s in self.filemap.values():
            if s.filetype == 'mhmodnl':
                s.modsig = None
                altpos = Position(repo=s.position.repo, directory=s.position.directory, modname=s.position.modname)
                if '.' in altpos.modname and altpos.modname.split('.')[-1] in LANGS:
                    altpos.modname = '.'.join(altpos.modname.split('.')[:-1])
                    f = self.__find_file(altpos)
                    if f and f.filetype == 'modsig':
                        s.modsig = f
                        continue
                self.ctx.log(LogEntry(LOG_ERROR, f'File appears to be an mhmodnl, but I failed to find a corresponding modsig', s.position, E_SYMB_LINK_ERROR))


        # STEP 3: LINK ALL REFERENCES
        for f in self.filemap.values():
            for m in f.collect_children([DEFI, TREFI]):
                s = self.__get_symbol(m)
                if not s:
                    self.ctx.log(LogEntry(LOG_ERROR, f'Failed to link "{m.match.group(0)}" to a symbol',
                        m.position, E_SYMB_LINK_ERROR))
                    continue
                if m in s.used: continue
                s.used.append(m)


        # STEP 4: LINK SYMBOL EVERYWHERE
        for s in self.get_all_symbols():
            for d in s.declared + s.used:
                s.symbol = s

    def get_all_symbols(self):
        for ss in self.symbols.values():
            for s in ss:
                yield s
                

    


    def __get_symbol(self, x):
        ''' only intended to be used during linking (as possibly inefficient) '''
        symb = x.symb

        if symb not in self.symbols:
            return None

        if isinstance(x, TREFI):
            mod = x.target_mod
            # long search for matching symbol... (BFS)
            # TODO: This doesn't consider module boundaries inside a file
            files = [x.lmhfile]
            ind = 0
            while ind < len(files):
                f = files[ind]
                ind += 1
                if not f: continue
                if f.filetype == 'mhmodnl':
                    files.append(f.modsig)
                for s in f.declared_symbols:
                    if s.module == mod and s.symb == symb:
                        return s
                for include in f.collect_children([USEMHMODULE, GUSE]):
                    ff = include.target_file
                    if not ff: continue
                    for s in ff.declared_symbols:
                        if s.module == mod and s.symb == symb:
                            return s
                for include in f.collect_children([IMPORTMHMODULE, GIMPORT]):
                    ff = include.target_file
                    if not ff: continue
                    if not ff in files:
                        files.append(ff)


        elif isinstance(x, DEFI) or isinstance(x, SYMI) or isinstance(x, SYMDEF):
            p = x.get_parent(goals=[MHMODNL, MODSIG, MODULE])
            if not p:
                self.ctx.log(LogEntry(LOG_ERROR, f'Failed to found surrounding module',
                    x.position, E_STEX_PARSE_ERROR))
                return None
            # key = (repo, p.position.directory if p.position.directory else '', mod
            for s in self.symbols[symb]:
                if s.repo == p.position.repo and s.module == p.mod and \
                        s.directory in ['', p.position.directory]:
                    return s
            return None

    


    def __find_file(self, position):
        if position.path and position.path in self.simplefilemap:
            return self.simplefilemap[position.path]
        directory = position.directory if position.directory else ''
        key = (position.repo, directory, position.modname)
        if key in self.filemap:
            return self.filemap[key]
        return None



    def __put_symbol(self, symbol):
        if symbol.symb in self.symbols:
            for s in self.symbols[symbol.symb]:
                if s.isSame(symbol):
                    s.merge(symbol)
                    return
            self.symbols[symbol.symb].append(symbol)
        self.symbols[symbol.symb] = [symbol]



