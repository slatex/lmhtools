import traceback
import os




# log levels
LOG_DEBUG = 0
LOG_INFO  = 1
LOG_WARN  = 2
LOG_ERROR = 3
LOG_FATAL = 4

# log entries
E_SKIP = 0                      # skipping something as expected (e.g. meta-inf or all.tex)
E_UNEXPECTED_EXCEPTION = 1
E_MISSING_MANIFEST = 2          # missing META-INF/MANIFEST.MF
E_MANIFEST_ERROR = 3            # error in META-INF/MANIFEST.MF
E_STEX_PARSE_ERROR = 4          # error while parsing stex
E_DUPLICATE_MODULE = 5
E_SYMB_LINK_ERROR = 6           # failed to link e.g. a trefi to a symbol



def exception_to_string(excp):
    ''' from stackoverflow '''
    stack = traceback.extract_stack()[:-3] + traceback.extract_tb(excp.__traceback__)  # add limit=??
    pretty = traceback.format_list(stack)
    return ''.join(pretty) + '\n  {} {}'.format(excp.__class__,excp)


class LogEntry(object):
    def __init__(self, loglevel, message, position, entrytype):
        self.loglevel  = loglevel
        self.message   = message
        self.position  = position
        self.entrytype = entrytype


# Thread-safe logger (wrt adding entries)
class Logger(object):
    def __init__(self, loglevel=2):
        self.loglevel = loglevel

        self.logs = []

    def log(self, entry):
        if entry.loglevel >= self.loglevel:
            self.logs.append(entry)

    def log_skip(self, message, position):
        self.log(LogEntry(LOG_DEBUG, message, position, E_SKIP))

    def log_fatal(self, message, exception, position):
        self.log(LogEntry(LOG_FATAL, message + os.linesep + exception_to_string(exception),
            position, E_UNEXPECTED_EXCEPTION))

    def print_logs(self):
        for entry in self.logs:
            print(f'{entry.position.toString()}: {entry.message}')

