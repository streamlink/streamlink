import unittest

from streamlink.plugins.tv360 import TV360


class TestPluginTV360(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://tv360.com.tr/CanliYayin',
        ]
        for url in should_match:
            self.assertTrue(TV360.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(TV360.can_handle_url(url))
