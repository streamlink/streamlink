# -*- coding: utf-8 -*-
from streamlink_cli.utils.progress import terminal_width, get_cut_prefix
import unittest


class TestCliUtilProgess(unittest.TestCase):
    def test_terminal_width(self):
        self.assertEqual(10, terminal_width("ABCDEFGHIJ"))
        self.assertEqual(30, terminal_width("A你好世界こんにちは안녕하세요B"))
        self.assertEqual(30, terminal_width("·「」『』【】-=！@#￥%……&×（）"))
        pass

    def test_get_cut_prefix(self):
        self.assertEqual("녕하세요CD",
                         get_cut_prefix("你好世界こんにちは안녕하세요CD", 10))
        self.assertEqual("하세요CD",
                         get_cut_prefix("你好世界こんにちは안녕하세요CD", 9))
        self.assertEqual("こんにちは안녕하세요CD",
                         get_cut_prefix("你好世界こんにちは안녕하세요CD", 23))
        pass
