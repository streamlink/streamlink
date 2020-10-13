import logging
from logging import NOTSET, ERROR, WARN, INFO, DEBUG, CRITICAL
from threading import Lock


TRACE = 5
_levelToName = dict([(CRITICAL, "critical"), (ERROR, "error"), (WARN, "warning"), (INFO, "info"), (DEBUG, "debug"),
                     (TRACE, "trace"), (NOTSET, "none")])
_nameToLevel = dict([(name, level) for level, name in _levelToName.items()])

for level, name in _levelToName.items():
    logging.addLevelName(level, name)

levels = [name for _, name in _levelToName.items()]
_config_lock = Lock()


class StreamlinkLogger(logging.getLoggerClass()):
    def trace(self, message, *args, **kws):
        if self.isEnabledFor(TRACE):
            self._log(TRACE, message, args, **kws)


logging.setLoggerClass(StreamlinkLogger)
root = logging.getLogger("streamlink")
root.setLevel(logging.WARNING)


class StringFormatter(logging.Formatter):
    def __init__(self, fmt, datefmt=None, style='%', remove_base=None):
        super(StringFormatter, self).__init__(fmt, datefmt=datefmt, style=style)
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


__all__ = ["StreamlinkLogger", "basicConfig", "root", "levels"]
