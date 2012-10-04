#!/usr/bin/env python

from .compat import bytes, is_py2

def isstring(val):
    if is_py2:
        return isinstance(val, str) or isinstance(val, unicode)
    else:
        return isinstance(val, str)

def byte(ordinal):
    if isstring(ordinal):
        ordinal = ord(ordinal)

    return bytes((ordinal,))

class flagproperty(object):
    def __init__(self, flags, attr, boolean=False):
        self.flags = flags
        self.attr = attr
        self.boolean = boolean

    def __get__(self, obj, cls):
        flags = getattr(obj, self.flags)
        val = getattr(flags.bit, self.attr)

        if self.boolean:
            val = bool(val)

        return val

    def __set__(self, obj, val):
        flags = getattr(obj, self.flags)
        setattr(flags.bit, self.attr, int(val))

def lang_to_iso639(lang):
    res = [0, 0, 0]

    for i in reversed(range(3)):
        res[i] = chr(0x60 + (lang & 0x1f))
        lang = lang >> 5

    return "".join(res)


def iso639_to_lang(iso639):
    res = 0

    for i in range(3):
        c = ord(iso639[i]) - 0x60
        res = res << 5
        res = res | c

    return res

__all__ = ["byte", "isstring", "flagproperty", "lang_to_iso639", "iso639_to_lang"]

