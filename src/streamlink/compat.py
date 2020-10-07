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

try:
    from urllib.parse import (
        urlparse, urlunparse, urljoin, quote, unquote, unquote_plus, parse_qsl, urlencode, urlsplit, urlunsplit
    )
    import queue
except ImportError:
    from urlparse import urlparse, urlunparse, urljoin, parse_qsl, urlsplit, urlunsplit
    from urllib import quote, unquote, unquote_plus, urlencode
    import Queue as queue


getargspec = getattr(inspect, "getfullargspec", inspect.getargspec)


__all__ = ["is_win32",
           "urlparse", "urlunparse", "urljoin", "parse_qsl", "quote",
           "unquote", "unquote_plus", "queue", "urlencode", "devnull",
           "urlsplit", "urlunsplit", "getargspec"]
