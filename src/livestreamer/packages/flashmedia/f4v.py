#!/usr/bin/env python

from .box import Box
from .compat import is_py2

class F4V(object):
    def __init__(self, fd=None):
        self.fd = fd

    def __iter__(self):
        return self

    def __next__(self):
        try:
            box = Box.deserialize(self.fd)
        except IOError:
            raise StopIteration

        return box

    if is_py2:
        next = __next__


__all__ = ["F4V"]
