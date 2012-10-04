#!/usr/bin/env python

class FLVError(Exception):
    pass

class F4VError(Exception):
    pass

class AMFError(Exception):
    pass

__all__ = ["FLVError", "F4VError", "AMFError"]
