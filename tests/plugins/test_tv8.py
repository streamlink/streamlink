import unittest

from streamlink.plugins.tv8 import TV8


class TestPluginTV8(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.tv8.com.tr/canli-yayin',
        ]
        for url in should_match:
            self.assertTrue(TV8.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(TV8.can_handle_url(url))
