import unittest

from streamlink.plugins.turkuvaz import Turkuvaz


class TestPluginTurkuvaz(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.atv.com.tr/webtv/canli-yayin',
            'http://www.a2tv.com.tr/webtv/canli-yayin',
            'https://www.ahaber.com.tr/webtv/canli-yayin',
            'https://www.aspor.com.tr/webtv/canli-yayin',
        ]
        for url in should_match:
            self.assertTrue(Turkuvaz.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Turkuvaz.can_handle_url(url))
