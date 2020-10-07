# -*- coding: utf-8 -*-
import unittest

from streamlink.utils.encoding import maybe_decode, maybe_encode


class TestUtilsEncoding(unittest.TestCase):
    def test_maybe_encode_py3(self):
        self.assertEqual(maybe_encode(u"test \u07f7"), u"test \u07f7")

    def test_maybe_decode_py3(self):
        self.assertEqual(maybe_decode(u"test \u07f7"), u"test \u07f7")
