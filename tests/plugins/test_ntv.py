import unittest

from streamlink.plugins.ntv import NTV


class TestPluginNTV(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.ntv.ru/air/',
            'http://www.ntv.ru/air/'
        ]
        for url in should_match:
            self.assertTrue(NTV.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://www.ntv.ru/',
            'http://www.ntv.ru/'
        ]
        for url in should_not_match:
            self.assertFalse(NTV.can_handle_url(url))
