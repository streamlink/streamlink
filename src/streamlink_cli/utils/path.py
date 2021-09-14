import re

from streamlink_cli.compat import is_win32


REPLACEMENT = "_"

_UNPRINTABLE = "".join(chr(c) for c in range(32))
_UNSUPPORTED_POSIX = "/"
_UNSUPPORTED_WIN32 = "\x7f\"*/:<>?\\|"

RE_CHARS_POSIX = re.compile("[{0}]+".format(re.escape(_UNPRINTABLE + _UNSUPPORTED_POSIX)))
RE_CHARS_WIN32 = re.compile("[{}]+".format(re.escape(_UNPRINTABLE + _UNSUPPORTED_WIN32)))
if is_win32:
    RE_CHARS = RE_CHARS_WIN32
else:
    RE_CHARS = RE_CHARS_POSIX


def replace_chars(path, charmap=None, replacement=REPLACEMENT):
    if charmap is None:
        pattern = RE_CHARS
    else:
        charmap = charmap.lower()
        if charmap in ("posix", "unix"):
            pattern = RE_CHARS_POSIX
        elif charmap in ("windows", "win32"):
            pattern = RE_CHARS_WIN32
        else:
            raise ValueError("Invalid charmap")

    return pattern.sub(replacement, path)
