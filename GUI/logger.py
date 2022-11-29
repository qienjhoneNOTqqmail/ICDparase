
import sys
from bunch import Bunch

# -------------------------------------------------------------------

class Logger:

    LEVELS = ("[TRACE]", "[INFO_]", "[WARN_]", "[ERROR]")

    def __init__(self, level, filename=None, console=False, progress=False):
        self._level = level
        self._filename = filename
        self._logfile = None
        self._console = console
        self._progress = progress
        self._progressvalue = 0
        if self._filename:
            self._logfile = open(self._filename, 'w')

    def progress(self, msg, incr):
            if self._progress:
                self._progressvalue += incr
                text = "PROGRESS:%d:%s\n" % (int(self._progressvalue), msg)
                sys.stderr.write(text)
                sys.stderr.flush()
    def logmsg(
            self,
            level,
            fmt,
            args,
            _levels= ("[TRACE]", "[INFO_]", "[WARN_]", "[ERROR]")
        ):
        if level >= self._level:
            text = _levels[level] + " " + (fmt % args) + '\n'
            self._logit(text)

    def nlogmsg(
            self,
            level,
            args,
            kwargs
        ):
        if level >= self._level:
            # [LEVEL] -- kwargs
            # [LEVEL] arg0 -- kwargs
            # [LEVEL] arg0: arg1 .. argN -- kwargs
            text = self.LEVELS[level]
            if len(args) == 0:
                text += ' --'
            elif len(args) == 1:
                text += ' ' + str(args[0]) 
            else:
                text += ' ' + str(args[0]) + ':'
                for t in args[1:]:
                    text += ' ' + str(t) 

            if len(kwargs):
                text += ' --'
                for key, val in kwargs.items():
                    text += ' ' + key.upper() + '=' + str(val)
            text += '\n'
            self._logit(text)
    
    def _logit(self, text):
            if self._logfile:
                self._logfile.write(text)
            if self._console:
                sys.stderr.write(text)

# -------------------------------------------------------------------

TRACE   = 0
INFO    = 1
WARN    = 2
ERROR   = 3

logger = None

def setup(level, filename=None, console=False, progress=False):
    global logger
    logger = Logger(level, filename, console, progress)

# initial logging calls

def info(fmt, *args):
    logger.logmsg(INFO, fmt, args)

def warn(fmt, *args):
    logger.logmsg(WARN, fmt, args)

def error(fmt, *args):
    logger.logmsg(ERROR, fmt, args)

def trace(fmt, *args):
    logger.logmsg(TRACE, fmt, args)

# new format calls
def progress(message, incr):
    logger.progress(message, incr)

def ninfo(*args, **kwargs):
    logger.nlogmsg(INFO, args, kwargs)

def nwarn(*args, **kwargs):
    logger.nlogmsg(WARN, args, kwargs)

def nerror(*args, **kwargs):
    logger.nlogmsg(ERROR, args, kwargs)

def ntrace(*args, **kwargs):
    logger.nlogmsg(TRACE, args, kwargs)

# Context version
def _context_formatter(msg, context):
    fmt = "%s: %s -- "
    args = (context[0], msg)
    for c in context[1:]:
        if isinstance(c, Bunch):
            fmt += "%s=%s "
            args += (c.TYPE, c.name)
        elif isinstance(c, tuple):
            fmt += "%s=%s "
            args += (c[0], c[1])
        else:
            fmt += "%s "
            args += str(c)
    return fmt, args

def cinfo(msg, context):
    fmt, args = _context_formatter(msg, context)
    logger.logmsg(INFO, fmt, args)

def cwarn(msg, context):
    fmt, args = _context_formatter(msg, context)
    logger.logmsg(WARN, fmt, args)

def cerror(msg, context):
    fmt, args = _context_formatter(msg, context)
    logger.logmsg(ERROR, fmt, args)

def ctrace(msg, context):
    fmt, args = _context_formatter(msg, context)
    logger.logmsg(TRACE, fmt, args)
