import unittest

from streamlink.plugins.kanal7 import Kanal7


class TestPluginKanal7(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://www.kanal7.com/canli-izle',
        ]
        for url in should_match:
            self.assertTrue(Kanal7.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Kanal7.can_handle_url(url))
