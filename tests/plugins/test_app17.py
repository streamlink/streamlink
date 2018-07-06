import unittest

from streamlink.plugins.app17 import App17


class TestPluginApp17(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://17.live/live/123123',
        ]
        for url in should_match:
            self.assertTrue(App17.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(App17.can_handle_url(url))
