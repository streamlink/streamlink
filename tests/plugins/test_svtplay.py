import unittest

from streamlink.plugins.svtplay import SVTPlay


class TestPluginSVTPlay(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.svtplay.se/video/16567350?start=auto',
        ]
        for url in should_match:
            self.assertTrue(SVTPlay.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(SVTPlay.can_handle_url(url))
