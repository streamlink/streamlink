#!/usr/bin/env python

from .box import Box, RawPayload
from .compat import is_py2


class F4V(object):
    def __init__(self, fd, strict=False, raw_payload=False):
        self.fd = fd
        self.raw_payload = raw_payload
        self.strict = strict

    def __iter__(self):
        return self

    def __next__(self):
        try:
            box = Box.deserialize(self.fd,
                                  strict=self.strict,
                                  raw_payload=self.raw_payload)
        except IOError:
            raise StopIteration

        return box

    if is_py2:
        next = __next__


__all__ = ["F4V"]
