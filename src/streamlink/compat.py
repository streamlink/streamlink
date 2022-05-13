import inspect
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
    from collections import Mapping
    from itertools import izip
    from singledispatch import singledispatch
    from typing import Callable

    def bytes(b, enc="ascii"):
        return _str(b)

    def indent(text, prefix, predicate=None):
        if predicate is None:
            def predicate(line):
                return line.strip()

        def prefixed_lines():
            for line in text.splitlines(True):
                yield (prefix + line if predicate(line) else line)
        return ''.join(prefixed_lines())

elif is_py3:
    bytes = bytes
    str = str
    range = range
    izip = zip
    from collections.abc import Callable, Mapping
    from functools import singledispatch
    from textwrap import indent

try:
    from re import Match
except ImportError:
    from typing import Match

try:
    from urllib.parse import (
        urlparse, urlunparse, urljoin, quote, quote_plus, unquote, unquote_plus, parse_qs,
        parse_qsl, urlencode, urlsplit, urlunsplit
    )
    import queue
except ImportError:
    from urlparse import urlparse, urlunparse, urljoin, parse_qs, parse_qsl, urlsplit, urlunsplit
    from urllib import quote, quote_plus, unquote, unquote_plus, urlencode
    import Queue as queue

try:
    from shutil import which
except ImportError:
    from backports.shutil_which import which

try:
    from html import unescape as html_unescape
except ImportError:
    from HTMLParser import HTMLParser
    html_unescape = unescape = HTMLParser().unescape

try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

getargspec = getattr(inspect, "getfullargspec", inspect.getargspec)


__all__ = ["Callable", "Mapping", "Match", "indent", "is_py2", "is_py3", "is_py33", "is_win32", "str", "bytes",
           "urlparse", "urlunparse", "urljoin", "parse_qs", "parse_qsl", "quote", "quote_plus",
           "unquote", "unquote_plus", "queue", "range", "singledispatch", "urlencode", "devnull", "which",
           "izip", "urlsplit", "urlunsplit", "getargspec", "html_unescape", "lru_cache"]
