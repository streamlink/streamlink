import unittest

from streamlink.plugins.nhkworld import NHKWorld


class TestPluginNHKWorld(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www3.nhk.or.jp/nhkworld/en/live/',
        ]
        for url in should_match:
            self.assertTrue(NHKWorld.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(NHKWorld.can_handle_url(url))
