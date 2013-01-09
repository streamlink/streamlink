#!/usr/bin/env python

from .box import Box, RawPayload
from .compat import is_py2

class F4V(object):
    def __init__(self, fd, strict=False, preload=True):
        self.fd = fd
        self.prev_box = None
        self.preload = preload
        self.strict = strict

    def __iter__(self):
        return self

    def __next__(self):
        # Consume previous box payload if needed
        if not self.preload and self.prev_box and \
           isinstance(self.prev_box.payload, RawPayload):
            self.prev_box.payload.read()

        try:
            box = Box.deserialize(self.fd,
                                  strict=self.strict,
                                  preload=self.preload)
        except IOError:
            raise StopIteration

        self.prev_box = box

        return box

    if is_py2:
        next = __next__


__all__ = ["F4V"]
