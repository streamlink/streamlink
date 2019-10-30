import unittest

from streamlink.plugins.kanalukraina import KanalUkraina


class TestPluginKanalUkraina(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://kanalukraina.tv/'
        ]
        for url in should_match:
            self.assertTrue(KanalUkraina.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://video.oz/'
        ]
        for url in should_not_match:
            self.assertFalse(KanalUkraina.can_handle_url(url))
