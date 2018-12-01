import unittest

from streamlink.plugins.stv import STV


class TestPluginSTV(unittest.TestCase):
    def test_can_handle_url(self):
        self.assertTrue(STV.can_handle_url('https://player.stv.tv/live'))
        self.assertTrue(STV.can_handle_url('http://player.stv.tv/live'))

    def test_can_handle_url_negative(self):
        self.assertFalse(STV.can_handle_url('http://example.com/live'))
