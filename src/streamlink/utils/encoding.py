from streamlink.compat import is_py2


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


__all__ = ["maybe_decode", "maybe_encode"]