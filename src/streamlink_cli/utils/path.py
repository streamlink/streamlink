import re
from pathlib import Path
from typing import Callable, Optional, Union

from streamlink.compat import is_win32


REPLACEMENT = "_"
SPECIAL_PATH_PARTS = (".", "..")

_UNPRINTABLE = "".join(chr(c) for c in range(32))
_UNSUPPORTED_POSIX = "/"
_UNSUPPORTED_WIN32 = "\x7f\"*/:<>?\\|"

RE_CHARS_POSIX = re.compile(f"[{re.escape(_UNPRINTABLE + _UNSUPPORTED_POSIX)}]+")
RE_CHARS_WIN32 = re.compile(f"[{re.escape(_UNPRINTABLE + _UNSUPPORTED_WIN32)}]+")
if is_win32:
    RE_CHARS = RE_CHARS_WIN32
else:
    RE_CHARS = RE_CHARS_POSIX


def replace_chars(path: str, charmap: Optional[str] = None, replacement: str = REPLACEMENT) -> str:
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
    if len(path) <= length:
        return path

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
    truncated = encoded[:length - len(parts[1]) - 1]
    decoded = truncated.decode("utf-8", errors="ignore")
    return f"{decoded}.{parts[1]}"


def replace_path(pathlike: Union[str, Path], mapper: Callable[[str], str]) -> Path:
    def get_part(part):
        newpart = mapper(part)
        return REPLACEMENT if part != newpart and newpart in SPECIAL_PATH_PARTS else newpart

    return Path(*(get_part(part) for part in Path(pathlike).expanduser().parts))
