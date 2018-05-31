import sys

if sys.version_info[0:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

__all__ = ['unittest']
