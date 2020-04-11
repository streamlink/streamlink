import unittest

from streamlink.plugins.galatasaraytv import KardelenTV


class TestPluginKardelenTV(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://kardelentv.com.tr/kardelen-tv-canli-izle/',
        ]
        for url in should_match:
            self.assertTrue(KardelenTV.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(KardelenTV.can_handle_url(url))
