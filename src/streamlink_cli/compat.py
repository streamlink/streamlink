import os
import re
import sys
from pathlib import Path

is_darwin = sys.platform == "darwin"
is_win32 = os.name == "nt"

stdout = sys.stdout.buffer

unprintable_ascii_chars = (chr(c) for c in range(32))

FS_SAFE_REPLACEMENT_CHAR = "_"
INVALID_FILENAME_CHARS = {
    "windows": "".join(unprintable_ascii_chars) + "\x7f\"*/:<>?\\|",
    "unix": "\x00/"
}


def make_fs_safe(unsafe_str, rules=None):
    if rules and rules in INVALID_FILENAME_CHARS:
        current_rules = rules
    else:
        if is_win32:
            current_rules = "windows"
        else:
            current_rules = "unix"

    sub_re = re.compile(
        "[{:s}]".format(re.escape(INVALID_FILENAME_CHARS[current_rules])), re.UNICODE
    )

    return sub_re.sub(FS_SAFE_REPLACEMENT_CHAR, unsafe_str)


class DeprecatedPath(type(Path())):
    pass


__all__ = ["is_darwin", "is_win32", "stdout", "make_fs_safe", "DeprecatedPath"]
