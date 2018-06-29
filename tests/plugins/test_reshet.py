import unittest

from streamlink.plugins.reshet import Reshet


class TestPluginReshet(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "https://www.reshet.tv/live",
            "http://www.reshet.tv/live",
            "http://reshet.tv/live",
            "https://reshet.tv/live",
            "http://reshet.tv/item/foo/bar123",
            "https://reshet.tv/item/foo/bar123",
            "https://www.reshet.tv/item/foo/bar123",
            "http://www.reshet.tv/item/foo/bar123",
        ]
        for url in should_match:
            self.assertTrue(Reshet.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            "https://www.youtube.com",
        ]
        for url in should_not_match:
            self.assertFalse(Reshet.can_handle_url(url))
