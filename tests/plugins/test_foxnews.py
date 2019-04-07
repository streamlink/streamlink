import unittest

from streamlink.plugins.ntv import Foxnews


class TestPluginFoxnews(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.foxnews.com/',
            'http://www.foxnews.com/'
            'https://video.foxnews.com/',
            'http://video.foxnews.com/'
        ]
        for url in should_match:
            self.assertTrue(Foxnews.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html'
        ]
        for url in should_not_match:
            self.assertFalse(Foxnews.can_handle_url(url))
