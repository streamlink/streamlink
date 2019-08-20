import unittest

from streamlink.plugins.arconai import ArconaiTv


class TestPluginArconaiTvTv(unittest.TestCase):
    def test_can_handle_url(self):
        self.assertTrue(ArconaiTv.can_handle_url('http://www.arconaitv.us/stream.php?id=25'))

    def test_can_handle_url_negative(self):
        self.assertFalse(ArconaiTv.can_handle_url('https://www.arconaitv.us/search.php'))
