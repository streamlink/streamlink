import unittest

from streamlink.plugins.arconai import ArconaiTv


class TestPluginArconaiTv(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(ArconaiTv.can_handle_url('http://arconaitv.co/stream.php?id=6'))
        self.assertTrue(ArconaiTv.can_handle_url('http://arconaitv.co/stream.php?id=24'))
        self.assertTrue(ArconaiTv.can_handle_url('http://arconaitv.co/stream.php?id=115'))

        # shouldn't match
        self.assertFalse(ArconaiTv.can_handle_url('http://arconaitv.co/'))
