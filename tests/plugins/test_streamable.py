import unittest

from streamlink.plugins.streamable import Streamable


class TestPluginStreamable(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://streamable.com/example',
        ]
        for url in should_match:
            self.assertTrue(Streamable.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Streamable.can_handle_url(url))
