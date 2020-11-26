import logging
from datetime import datetime
from logging import CRITICAL, DEBUG, ERROR, INFO, NOTSET, WARN
from threading import Lock

TRACE = 5
_levelToName = {
    CRITICAL: "critical",
    ERROR: "error",
    WARN: "warning",
    INFO: "info",
    DEBUG: "debug",
    TRACE: "trace",
    NOTSET: "none",
}
_nameToLevel = {name: level for level, name in _levelToName.items()}

for level, name in _levelToName.items():
    logging.addLevelName(level, name)

levels = [name for _, name in _levelToName.items()]
_config_lock = Lock()


class StreamlinkLogger(logging.getLoggerClass()):
    def trace(self, message, *args, **kws):
        if self.isEnabledFor(TRACE):
            self._log(TRACE, message, args, **kws)


class StringFormatter(logging.Formatter):
    def __init__(self, fmt, datefmt=None, style="%", remove_base=None):
        if style not in ("{", "%"):
            raise ValueError("Only {} and % formatting styles are supported")
        super().__init__(fmt, datefmt=datefmt, style=style)
        self.style = style
        self.fmt = fmt
        self.remove_base = remove_base or []
        self._usesTime = (style == "%" and "%(asctime)" in fmt) or (style == "{" and "{asctime}" in fmt)

    def usesTime(self):
        return self._usesTime

    def formatTime(self, record, datefmt=None):
        tdt = datetime.fromtimestamp(record.created)

        return tdt.strftime(datefmt or self.default_time_format)

    def formatMessage(self, record):
        if self.style == "{":
            return self.fmt.format(**record.__dict__)
        else:
            return self.fmt % record.__dict__

    def format(self, record):
        for rbase in self.remove_base:
            record.name = record.name.replace(rbase + ".", "")
        record.levelname = record.levelname.lower()

        return super().format(record)


def basicConfig(**kwargs):
    with _config_lock:
        filename = kwargs.get("filename")
        if filename:
            mode = kwargs.get("filemode", "a")
            handler = logging.FileHandler(filename, mode)
        else:
            stream = kwargs.get("stream")
            handler = logging.StreamHandler(stream)
        fs = kwargs.get("format", BASIC_FORMAT)
        style = kwargs.get("style", FORMAT_STYLE)
        dfs = kwargs.get("datefmt", FORMAT_DATE)
        remove_base = kwargs.get("remove_base", REMOVE_BASE)

        formatter = StringFormatter(fs, dfs, style=style, remove_base=remove_base)
        handler.setFormatter(formatter)

        root.addHandler(handler)
        level = kwargs.get("level")
        if level is not None:
            root.setLevel(level)


BASIC_FORMAT = "[{name}][{levelname}] {message}"
FORMAT_STYLE = "{"
FORMAT_DATE = "%H:%M:%S"
REMOVE_BASE = ["streamlink", "streamlink_cli"]


logging.setLoggerClass(StreamlinkLogger)
root = logging.getLogger("streamlink")
root.setLevel(logging.WARNING)


__all__ = ["StreamlinkLogger", "basicConfig", "root", "levels"]
