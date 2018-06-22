from sys import getfilesystemencoding

from streamlink.compat import is_win32, is_py2


def get_filesystem_encoding():
    file_system_encoding = getfilesystemencoding()
    if file_system_encoding is None:  # `None` not possible after python 3.2
        if is_win32:
            file_system_encoding = 'mbcs'
        else:
            file_system_encoding = 'utf-8'
    return file_system_encoding


def maybe_encode(text, encoding="utf8"):
    if is_py2:
        return text.encode(encoding)
    else:
        return text


def maybe_decode(text, encoding="utf8"):
    if is_py2 and isinstance(text, str):
        return text.decode(encoding)
    else:
        return text


__all__ = ["get_filesystem_encoding", "maybe_decode", "maybe_encode"]
