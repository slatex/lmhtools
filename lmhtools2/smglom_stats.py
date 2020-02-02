''' Tool for generating smglom statistics '''

from lmh_harvest import *
from lmh_logging import *

import os
import sys

mh = os.path.realpath(os.path.abspath(sys.argv[1]))

harvester = Harvester(Logger(2), mh)

harvester.load_files('^smglom/.*$')

harvester.ctx.referencer.compile()


symbols = list(harvester.ctx.referencer.get_all_symbols())

symbols.sort(key = lambda s : len(s.used))
symbols.reverse()

print("MOST REFERENCED SYMBOLS:")
for i in range(10):
    print(f'{i+1}: {symbols[i].symb}    ({len(symbols[i].used)} times)')


total_mods = 0
for f in harvester.files:
    if f.filetype in ['module', 'modsig']:
        total_mods += 1


total_symbols = len(symbols)

coverage = {}

for s in symbols:
    used = []
    for u in s.used:
        if u.lang and u.lang not in used:
            used.append(u.lang)

    for u in used:
        if u not in coverage:
            coverage[u] = 0
        coverage[u] += 1

print("TOTAL SYMBOLS:", total_symbols)
print("COVERAGE:")
for k in coverage:
    print(f'{k}: {100*coverage[k]/total_symbols:.1f}%')

