#!/usr/bin/env python

import sys

is_py2 = (sys.version_info[0] == 2)
is_py3 = (sys.version_info[0] == 3)

if is_py2:
    str = unicode
    input = raw_input

    def bytes(b, enc="ascii"):
        return str(b)

elif is_py3:
    str = str
    bytes = bytes
    input = input

try:
    import urllib.request as urllib
except ImportError:
    import urllib2 as urllib

try:
    from urllib.parse import urlparse, parse_qs
except ImportError:
    from urlparse import urlparse, parse_qs
