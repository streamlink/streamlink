import unittest

from streamlink.plugins.younow import YouNow


class TestPluginYouNow(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.younow.com/example',
        ]
        for url in should_match:
            self.assertTrue(YouNow.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(YouNow.can_handle_url(url))
