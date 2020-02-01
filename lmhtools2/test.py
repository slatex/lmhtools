from lmh_harvest import *
from lmh_logging import *

import os
mh = os.path.realpath(os.path.abspath('/home/jfs/git/gl_mathhub_info'))

harvester = Harvester(Logger(2), mh)

# harvester.load_files()
harvester.load_file('/home/jfs/git/gl_mathhub_info/smglom/sets/source/emptyset.en.tex')

harvester.logger.print_logs()

print(harvester.files[0].collect_children([DEFI]))
print(harvester.files[0].collect_children([DEFI],[MHMODNL]))
