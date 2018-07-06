import unittest

from streamlink.plugins.cybergame import Cybergame


class TestPluginCybergame(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://cybergame.tv/example/',
            'https://cybergame.tv/videos/123123123/123123123-/'
        ]
        for url in should_match:
            self.assertTrue(Cybergame.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Cybergame.can_handle_url(url))
