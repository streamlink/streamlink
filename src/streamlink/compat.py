import os
import inspect

is_win32 = os.name == "nt"

# win/nix compatible devnull
try:
    from subprocess import DEVNULL

    def devnull():
        return DEVNULL
except ImportError:
    def devnull():
        return open(os.path.devnull, 'w')

bytes = bytes
str = str
range = range
izip = zip

try:
    from urllib.parse import (
        urlparse, urlunparse, urljoin, quote, unquote, unquote_plus, parse_qsl, urlencode, urlsplit, urlunsplit
    )
    import queue
except ImportError:
    from urlparse import urlparse, urlunparse, urljoin, parse_qsl, urlsplit, urlunsplit
    from urllib import quote, unquote, unquote_plus, urlencode
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


getargspec = getattr(inspect, "getfullargspec", inspect.getargspec)


__all__ = ["is_win32", "str", "bytes",
           "urlparse", "urlunparse", "urljoin", "parse_qsl", "quote",
           "unquote", "unquote_plus", "queue", "range", "urlencode", "devnull", "which",
           "izip", "urlsplit", "urlunsplit", "getargspec", "html_unescape"]
