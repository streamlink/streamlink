import unittest

from streamlink.plugins.arconai import ArconaiTv


class TestPluginArconaiTv(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(ArconaiTv.can_handle_url('http://arconaitv.me/stream.php?id=1'))
        self.assertTrue(ArconaiTv.can_handle_url('http://arconaitv.me/stream.php?id=23'))
        self.assertTrue(ArconaiTv.can_handle_url('http://arconaitv.me/stream.php?id=440'))

        # shouldn't match
        self.assertFalse(ArconaiTv.can_handle_url('http://arconaitv.me/'))
