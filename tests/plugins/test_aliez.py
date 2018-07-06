import unittest

from streamlink.plugins.aliez import Aliez


class TestPluginAliez(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://aliez.tv/live/stream1_11111/',
            'http://aliez.tv/video/100000/ABCabc123/'
        ]
        for url in should_match:
            self.assertTrue(Aliez.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Aliez.can_handle_url(url))
