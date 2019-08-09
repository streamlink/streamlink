import unittest

from streamlink.plugins.oneplusone import OnePlusOne


class TestPluginOnePlusOne(unittest.TestCase):

    def test_can_handle_url(self):
        should_match = [
            'https://1plus1.video/tvguide/1plus1/online',
            'https://1plus1.video/tvguide/2plus2/online',
            'https://1plus1.video/tvguide/tet/online',
            'https://1plus1.video/tvguide/plusplus/online',
            'https://1plus1.video/tvguide/bigudi/online',
            'https://1plus1.video/tvguide/uniantv/online',
        ]
        for url in should_match:
            self.assertTrue(OnePlusOne.can_handle_url(url), url)

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com',
            'https://1plus1.video/',
        ]
        for url in should_not_match:
            self.assertFalse(OnePlusOne.can_handle_url(url), url)
