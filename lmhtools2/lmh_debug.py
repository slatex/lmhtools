''' Tool for finding stex problems in LMH '''

from lmh_harvest import *
from lmh_logging import *

import os
import sys

mh = os.path.realpath(os.path.abspath(sys.argv[1]))

harvester = Harvester(Logger(2), mh)

harvester.load_files('^(MiKoMH|smglom)/.*$')

harvester.logger.print_logs()

