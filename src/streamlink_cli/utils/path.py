from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from streamlink.compat import is_win32


REPLACEMENT = "_"
SPECIAL_PATH_PARTS = (".", "..")

_UNPRINTABLE = "".join(chr(c) for c in range(32))
_UNSUPPORTED_POSIX = "/"
_UNSUPPORTED_WIN32 = '\x7f"*/:<>?\\|'

RE_CHARS_POSIX = re.compile(f"[{re.escape(_UNPRINTABLE + _UNSUPPORTED_POSIX)}]+")
RE_CHARS_WIN32 = re.compile(f"[{re.escape(_UNPRINTABLE + _UNSUPPORTED_WIN32)}]+")
if is_win32:
    RE_CHARS = RE_CHARS_WIN32
else:
    RE_CHARS = RE_CHARS_POSIX


def replace_chars(path: str, charmap: str | None = None, replacement: str = REPLACEMENT) -> str:
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


# This method does not take care of unicode modifier characters when truncating
def truncate_path(path: str, length: int = 255, keep_extension: bool = True) -> str:
    parts = path.rsplit(".", 1)

    # no file name extension (no dot separator in path or file name extension too long):
    # truncate the whole thing
    if not keep_extension or len(parts) == 1 or len(parts[1]) > 10:
        encoded = path.encode("utf-8")
        truncated = encoded[:length]
        decoded = truncated.decode("utf-8", errors="ignore")
        return decoded

    # truncate file name, but keep file name extension
    encoded = parts[0].encode("utf-8")
    truncated = encoded[: length - len(parts[1]) - 1]
    decoded = truncated.decode("utf-8", errors="ignore")
    return f"{decoded}.{parts[1]}"


def replace_path(pathlike: str | Path, mapper: Callable[[str, bool], str]) -> Path:
    def get_part(part: str, isfile: bool) -> str:
        newpart = mapper(part, isfile)
        return REPLACEMENT if part != newpart and newpart in SPECIAL_PATH_PARTS else newpart

    parts = Path(pathlike).expanduser().parts
    last = len(parts) - 1

    return Path(*(get_part(part, i == last) for i, part in enumerate(parts)))
