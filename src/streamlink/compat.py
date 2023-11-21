import os
import sys


# compatibility import of charset_normalizer/chardet via requests<3.0
try:
    from requests.compat import chardet as charset_normalizer  # type: ignore
except ImportError:  # pragma: no cover
    import charset_normalizer


is_darwin = sys.platform == "darwin"
is_win32 = os.name == "nt"


detect_encoding = charset_normalizer.detect


__all__ = [
    "is_darwin",
    "is_win32",
    "detect_encoding",
]
