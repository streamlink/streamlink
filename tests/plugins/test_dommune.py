import unittest

from streamlink.plugins.dommune import Dommune


class TestPluginDommune(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://dommune.com',
        ]
        for url in should_match:
            self.assertTrue(Dommune.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Dommune.can_handle_url(url))
