#!/usr/bin/env python

from .error import FLVError
from .compat import is_py2
from .tag import Header, Tag


class FLV(object):
    def __init__(self, fd=None, strict=False):
        self.fd = fd
        self.header = Header.deserialize(self.fd)
        self.strict = strict

    def __iter__(self):
        return self

    def __next__(self):
        try:
            tag = Tag.deserialize(self.fd, strict=self.strict)
        except (IOError, FLVError):
            raise StopIteration

        return tag

    if is_py2:
        next = __next__


__all__ = ["FLV"]
