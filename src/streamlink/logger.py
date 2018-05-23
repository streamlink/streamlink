import logging
import warnings

from streamlink.compat import is_py2
from logging import NOTSET, ERROR, WARN, INFO, DEBUG, CRITICAL

TRACE = 5
logging.addLevelName(CRITICAL, "critical")
logging.addLevelName(ERROR, "error")
logging.addLevelName(WARN, "warning")
logging.addLevelName(INFO, "info")
logging.addLevelName(DEBUG, "debug")
logging.addLevelName(TRACE, "trace")
logging.addLevelName(NOTSET, "none")


def trace(self, message, *args, **kws):
    # Yes, logger takes its '*args' as 'args'.
    self._log(TRACE, message, args, **kws)

logging.Logger.trace = trace
root = logging.getLogger("streamlink")
levels = [logging.getLevelName(l) for l in (NOTSET, CRITICAL, ERROR, WARN, INFO, DEBUG, TRACE)]


class DeprecatedLogger(object):
    """
    Wrapper to warn developers when using deprecated logging methods
    """
    def __init__(self, logger):
        self.__logger = logger

    def __getattr__(self, item):
        if item in self.__dict__:
            return getattr(self, item)
        warnings.warn("This logging method has been deprecated, use the standard logging module", DeprecationWarning)
        return getattr(self.__logger, item)



class _CompatLogRecord(logging.LogRecord):
    """
    LogRecord wrapper to include sinfo for Python 3 by not Python 2
    """
    def __init__(self, name, level, pathname, lineno, msg, args, exc_info, func=None, sinfo=None, **kwargs):
        if is_py2:
            super(_CompatLogRecord, self).__init__(name, level, pathname, lineno, msg, args, exc_info, func=func)
        else:
            super(_CompatLogRecord, self).__init__(name, level, pathname, lineno, msg, args, exc_info, func=func, sinfo=sinfo, **kwargs)


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


class StreamlinkLogger(logging.getLoggerClass()):
    def __init__(self, name):
        super(StreamlinkLogger, self).__init__(name)

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

    set_level = root.setLevel  # set log level for the root streamlink logger

    @staticmethod
    def new_module(name):
        warnings.warn("Logger.new_module has been deprecated, use the standard logging.getLogger method",
                      DeprecationWarning)
        return logging.getLogger("streamlink.{0}".format(name))

    @staticmethod
    def set_output(output):
        """
        No-op, must be set in the log handler
        """
        warnings.warn("Logger.set_output has been deprecated, use the standard logging module",
                      DeprecationWarning)


class StringFormatter(logging.Formatter):
    def format(self, record):
        record.name = record.name.replace("streamlink.", "").replace("streamlink_cli.", "")
        record.levelname = record.levelname.lower()
        return super(StringFormatter, self).format(record)


__all__ = ["StreamlinkLogHandler", "DeprecatedLogger", "root", "levels"]
