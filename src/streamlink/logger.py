import logging
import warnings

import sys
from threading import Lock

from streamlink.compat import is_py2
from logging import NOTSET, ERROR, WARN, INFO, DEBUG, CRITICAL

TRACE = 5
_levelToName = dict([(CRITICAL, "critical"), (ERROR, "error"), (WARN, "warning"), (INFO, "info"), (DEBUG, "debug"),
                     (TRACE, "trace"), (NOTSET, "none")])
_nameToLevel = dict([(name, level) for level, name in _levelToName.items()])

for level, name in _levelToName.items():
    logging.addLevelName(level, name)

levels = [name for _, name in _levelToName.items()]
_config_lock = Lock()


class _CompatLogRecord(logging.LogRecord):
    """
    LogRecord wrapper to include sinfo for Python 3 by not Python 2
    """

    def __init__(self, name, level, pathname, lineno, msg, args, exc_info, func=None, sinfo=None, **kwargs):
        if is_py2:
            super(_CompatLogRecord, self).__init__(name, level, pathname, lineno, msg, args, exc_info, func=func)
        else:
            super(_CompatLogRecord, self).__init__(name, level, pathname, lineno, msg, args, exc_info, func=func,
                                                   sinfo=sinfo, **kwargs)


class _LogRecord(_CompatLogRecord):
    def getMessage(self):
        """
        Return the message for this LogRecord.

        Return the message for this LogRecord after merging any user-supplied
        arguments with the message.
        """
        msg = str(self.msg)
        if self.args:
            msg = msg.format(*self.args)
        return msg


class StreamlinkLogger(logging.getLoggerClass(), object):
    def __init__(self, name, level=logging.NOTSET):
        super(StreamlinkLogger, self).__init__(name, level)

    def trace(self, message, *args, **kws):
        if self.isEnabledFor(TRACE):
            self._log(TRACE, message, args, **kws)

    def makeRecord(self, name, level, fn, lno, msg, args, exc_info,
                   func=None, extra=None, sinfo=None):
        """
        A factory method which can be overridden in subclasses to create
        specialized LogRecords.
        """
        if name.startswith("streamlink"):
            rv = _LogRecord(name, level, fn, lno, msg, args, exc_info, func, sinfo)
        else:
            rv = _CompatLogRecord(name, level, fn, lno, msg, args, exc_info, func, sinfo)
        if extra is not None:
            for key in extra:
                if (key in ["message", "asctime"]) or (key in rv.__dict__):
                    raise KeyError("Attempt to overwrite %r in LogRecord" % key)
                rv.__dict__[key] = extra[key]
        return rv

    def set_level(self, level):
        self.setLevel(level)

    @staticmethod
    def new_module(name):
        warnings.warn("Logger.new_module has been deprecated, use the standard logging.getLogger method",
                      category=DeprecationWarning, stacklevel=2)
        return logging.getLogger("streamlink.{0}".format(name))

    @staticmethod
    def set_output(output):
        """
        No-op, must be set in the log handler
        """
        warnings.warn("Logger.set_output has been deprecated, use the standard logging module",
                      category=DeprecationWarning, stacklevel=2)


logging.setLoggerClass(StreamlinkLogger)
root = logging.getLogger("streamlink")
root.setLevel(logging.WARNING)


class StringFormatter(logging.Formatter):
    def __init__(self, fmt, datefmt=None, style='%', remove_base=None):
        super(StringFormatter, self).__init__(fmt, datefmt=datefmt)
        if style not in ("{", "%"):
            raise ValueError("Only {} and % formatting styles are supported")
        self.style = style
        self.fmt = fmt
        self.remove_base = remove_base or []

    def usesTime(self):
        return (self.style == "%" and "%(asctime)" in self.fmt) or (self.style == "{" and "{asctime}" in self.fmt)

    def formatMessage(self, record):
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        if self.style == "{":
            return self.fmt.format(**record.__dict__)
        else:
            return self.fmt % record.__dict__

    def format(self, record):
        for rbase in self.remove_base:
            record.name = record.name.replace(rbase + ".", "")
        record.levelname = record.levelname.lower()

        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)

        s = self.formatMessage(record)

        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            s += "\n" if not s.endswith("\n") else "" + record.exc_text
        return s


class Logger(object):
    Levels = levels
    Format = "[{name}][{levelname}] {message}"
    root_name = "streamlink_old"

    def __init__(self):
        warnings.warn("Logger class has been deprecated, use the standard logging module",
                      category=DeprecationWarning, stacklevel=2)
        self.root = logging.getLogger(self.root_name)
        root.propagate = False
        self.handler = logging.StreamHandler(sys.stdout)
        self.handler.setFormatter(StringFormatter(self.Format, style="{", remove_base=[self.root_name]))
        self.root.addHandler(self.handler)
        self.set_level("info")

    @classmethod
    def get_logger(cls, name):
        return logging.getLogger("{0}.{1}".format(cls.root_name, name))

    def new_module(self, module):
        return LoggerModule(self, module)

    def set_level(self, level):
        self.root.setLevel(level)

    def set_output(self, output):
        self.handler.stream = output

    def msg(self, module, level, msg, *args, **kwargs):
        log = self.get_logger(module)
        log.log(level, msg, *args)


class LoggerModule(object):
    def __init__(self, manager, module):
        warnings.warn("LoggerModule class has been deprecated, use the standard logging module",
                      category=DeprecationWarning, stacklevel=2)
        self.manager = manager
        self.module = module

    def error(self, msg, *args, **kwargs):
        self.manager.msg(self.module, ERROR, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.manager.msg(self.module, WARN, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.manager.msg(self.module, INFO, msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.manager.msg(self.module, DEBUG, msg, *args, **kwargs)


BASIC_FORMAT = "[{name}][{levelname}] {message}"
FORMAT_STYLE = "{"
REMOVE_BASE = ["streamlink", "streamlink_cli"]


def basicConfig(**kwargs):
    with _config_lock:
        filename = kwargs.get("filename")
        if filename:
            mode = kwargs.get("filemode", 'a')
            handler = logging.FileHandler(filename, mode)
        else:
            stream = kwargs.get("stream")
            handler = logging.StreamHandler(stream)
        fs = kwargs.get("format", BASIC_FORMAT)
        style = kwargs.get("style", FORMAT_STYLE)
        dfs = kwargs.get("datefmt", None)
        remove_base = kwargs.get("remove_base", REMOVE_BASE)

        formatter = StringFormatter(fs, dfs, style=style, remove_base=remove_base)
        handler.setFormatter(formatter)

        root.addHandler(handler)
        level = kwargs.get("level")
        if level is not None:
            root.setLevel(level)


__all__ = ["StreamlinkLogger", "Logger", "basicConfig", "root", "levels"]
