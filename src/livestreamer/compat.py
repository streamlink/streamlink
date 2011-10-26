#!/usr/bin/env python

import sys

orig_str = str

def str(s, enc="ascii"):
    if sys.version_info[0] == 3:
        return orig_str(s, enc)
    else:
        return orig_str(s)


orig_bytes = bytes

def bytes(s, enc="ascii"):
    if sys.version_info[0] == 3:
        return orig_bytes(s, enc)
    else:
        return orig_bytes(s)

try:
    import urllib.request as urllib
except ImportError:
    import urllib2 as urllib

