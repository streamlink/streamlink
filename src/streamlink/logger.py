import logging
import sys
from datetime import datetime
from logging import CRITICAL, DEBUG, ERROR, INFO, WARNING
from pathlib import Path
from threading import Lock
from typing import IO, List, Optional, TYPE_CHECKING, Union


FORMAT_STYLE = "{"
FORMAT_BASE = "[{name}][{levelname}] {message}"
FORMAT_DATE = "%H:%M:%S"
REMOVE_BASE = ["streamlink", "streamlink_cli"]

# Make NONE ("none") the highest possible level that suppresses all log messages:
#  `logging.NOTSET` (equal to 0) can't be used as the "none" level because of `logging.Logger.getEffectiveLevel()`, which
#  loops through the logger instance's ancestor chain and checks whether the instance's level is NOTSET. If it is NOTSET,
#  then it continues with the parent logger, which means that if the level of `streamlink.logger.root` was set to "none" and
#  its value NOTSET, then it would continue with `logging.root` whose default level is `logging.WARNING` (equal to 30).
NONE = sys.maxsize
# Add "trace" to Streamlink's log levels
TRACE = 5

# Define Streamlink's log levels (and register both lowercase and uppercase names)
_levelToNames = {
    NONE: "none",
    CRITICAL: "critical",
    ERROR: "error",
    WARNING: "warning",
    INFO: "info",
    DEBUG: "debug",
    TRACE: "trace",
}

for _level, _name in _levelToNames.items():
    logging.addLevelName(_level, _name.upper())
    logging.addLevelName(_level, _name)

_config_lock = Lock()


if TYPE_CHECKING:  # pragma: no cover
    _BaseLoggerClass = logging.Logger
else:
    _BaseLoggerClass = logging.getLoggerClass()


class StreamlinkLogger(_BaseLoggerClass):
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
            record.name = record.name.replace(f"{rbase}.", "")
        record.levelname = record.levelname.lower()

        return super().format(record)


# noinspection PyShadowingBuiltins,PyPep8Naming
def basicConfig(
    filename: Optional[Union[str, Path]] = None,
    filemode: str = "a",
    stream: Optional[IO] = None,
    level: Optional[str] = None,
    format: str = FORMAT_BASE,
    style: str = FORMAT_STYLE,  # TODO: py38: Literal["%", "{", "$"]
    datefmt: str = FORMAT_DATE,
    remove_base: Optional[List[str]] = None
) -> logging.StreamHandler:
    with _config_lock:
        handler: logging.StreamHandler
        if filename is not None:
            handler = logging.FileHandler(filename, filemode)
        else:
            handler = logging.StreamHandler(stream)

        # noinspection PyTypeChecker
        formatter = StringFormatter(
            format,
            datefmt,
            style=style,
            remove_base=remove_base or REMOVE_BASE
        )
        handler.setFormatter(formatter)

        root.addHandler(handler)
        if level is not None:
            root.setLevel(level)

    return handler


logging.setLoggerClass(StreamlinkLogger)
root = logging.getLogger("streamlink")
root.setLevel(WARNING)

levels = list(_levelToNames.values())


__all__ = [
    "NONE",
    "TRACE",
    "StreamlinkLogger",
    "basicConfig",
    "root",
    "levels",
]
