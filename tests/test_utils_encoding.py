# -*- coding: utf-8 -*-
import unittest

from streamlink.compat import is_py3, is_py2
from streamlink.utils.encoding import maybe_decode, maybe_encode


class TestUtilsEncoding(unittest.TestCase):

    @unittest.skipUnless(is_py2, "only applicable in Python 2")
    def test_maybe_encode_py2(self):
        self.assertEqual(maybe_encode(u"test \u07f7"), "test \xdf\xb7")

    @unittest.skipUnless(is_py2, "only applicable in Python 2")
    def test_maybe_decode_py2(self):
        self.assertEqual(maybe_decode("test \xdf\xb7"), u"test \u07f7")

    @unittest.skipUnless(is_py3, "only applicable in Python 3")
    def test_maybe_encode_py3(self):
        self.assertEqual(maybe_encode(u"test \u07f7"), u"test \u07f7")

    @unittest.skipUnless(is_py3, "only applicable in Python 3")
    def test_maybe_decode_py3(self):
        self.assertEqual(maybe_decode(u"test \u07f7"), u"test \u07f7")
