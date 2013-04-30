import os
import sys

is_py2 = (sys.version_info[0] == 2)
is_py3 = (sys.version_info[0] == 3)
is_win32 = os.name == "nt"

if is_py2:
    _str = str
    str = unicode
    range = xrange
    string_types = (_str, unicode)
    integer_types = (int, long)

    def bytes(b=None, enc="ascii"):
        if b is None:
            return ""
        elif isinstance(b, list) or isinstance(b, tuple):
            return "".join([chr(i) for i in b])
        else:
            return _str(b)

elif is_py3:
    bytes = bytes
    str = str
    range = range
    string_types = (str,)
    integer_types = (int,)


try:
    from collections import OrderedDict
except ImportError:
    from .ordereddict import OrderedDict

__all__ = ["is_py2", "is_py3", "is_win32", "str", "bytes", "range",
           "OrderedDict"]
