import unittest

from streamlink.plugins.latina import Latina


class TestPluginLatina(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://www.latina.pe/tvenvivo/',
        ]
        for url in should_match:
            self.assertTrue(Latina.can_handle_url(url), url)

    def test_can_handle_url_negative(self):
        should_not_match = [
            'http://www.latina.pe/',
        ]
        for url in should_not_match:
            self.assertFalse(Latina.can_handle_url(url), url)
