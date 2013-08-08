import os
import sys

is_py2 = (sys.version_info[0] == 2)
is_py3 = (sys.version_info[0] == 3)
is_py33 = (sys.version_info[0] == 3 and sys.version_info[1] == 3)
is_win32 = os.name == "nt"

if is_py2:
    _str = str
    str = unicode
    range = xrange

    def bytes(b, enc="ascii"):
        return _str(b)

elif is_py3:
    bytes = bytes
    str = str
    range = range

try:
    from urllib.parse import urlparse, urljoin, quote, unquote, parse_qsl
    import queue
except ImportError:
    from urlparse import urlparse, urljoin, parse_qsl
    from urllib import quote, unquote
    import Queue as queue

__all__ = ["is_py2", "is_py3", "is_py33", "is_win32", "str", "bytes",
           "urlparse", "urljoin", "parse_qsl", "quote", "unquote", "queue",
           "range"]
