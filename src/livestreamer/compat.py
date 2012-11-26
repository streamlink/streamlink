import os
import sys

is_py2 = (sys.version_info[0] == 2)
is_py3 = (sys.version_info[0] == 3)
is_win32 = os.name == "nt"

if is_py2:
    input = raw_input
    stdout = sys.stdout
    _str = str
    str = unicode
    file = file

    def bytes(b, enc="ascii"):
        return _str(b)

elif is_py3:
    bytes = bytes
    input = input
    stdout = sys.stdout.buffer
    str = str
    from io import IOBase as file

try:
    from urllib.parse import urlparse, urljoin, quote, unquote, parse_qs
    import queue
except ImportError:
    from urlparse import urlparse, urljoin, parse_qs
    from urllib import quote, unquote
    import Queue as queue

if is_win32:
    import pbs as sh
    pbs_compat = True
else:
    import sh
    pbs_compat = False

__all__ = ["is_py2", "is_py3", "is_win32", "input", "stdout",
           "str", "bytes", "urlparse", "urljoin", "parse_qs",
           "quote", "unquote", "sh", "pbs_compat", "queue"]
