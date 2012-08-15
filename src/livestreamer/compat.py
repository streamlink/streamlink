import sys, os

is_py2 = (sys.version_info[0] == 2)
is_py3 = (sys.version_info[0] == 3)
is_win32 = os.name == "nt"

if is_py2:
    input = raw_input
    stdout = sys.stdout
    str = unicode

    def bytes(b, enc="ascii"):
        return str(b)

elif is_py3:
    bytes = bytes
    input = input
    stdout = sys.stdout.buffer
    str = str

try:
    import urllib.request as urllib
except ImportError:
    import urllib2 as urllib

try:
    from urllib.parse import urlparse, parse_qs
except ImportError:
    from urlparse import urlparse, parse_qs

__all__ = ["is_py2", "is_py3", "is_win32", "input", "stdout", "str",
           "bytes", "urllib", "urlparse", "parse_qs"]
