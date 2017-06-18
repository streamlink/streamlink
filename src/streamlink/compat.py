import os
import sys

is_py2 = (sys.version_info[0] == 2)
is_py3 = (sys.version_info[0] == 3)
is_py33 = (sys.version_info[0] == 3 and sys.version_info[1] == 3)
is_win32 = os.name == "nt"

# win/nix compatible devnull
try:
    from subprocess import DEVNULL

    def devnull():
        return DEVNULL
except ImportError:
    def devnull():
        return open(os.path.devnull, 'w')

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
    from urllib.parse import (
        urlparse, urlunparse, urljoin, quote, unquote, parse_qsl, urlencode
    )
    import queue
except ImportError:
    from urlparse import urlparse, urlunparse, urljoin, parse_qsl
    from urllib import quote, unquote, urlencode
    import Queue as queue

try:
    from shutil import which
except ImportError:
    from backports.shutil_which import which


__all__ = ["is_py2", "is_py3", "is_py33", "is_win32", "str", "bytes",
           "urlparse", "urlunparse", "urljoin", "parse_qsl", "quote",
           "unquote", "queue", "range", "urlencode", "devnull", "which"]
