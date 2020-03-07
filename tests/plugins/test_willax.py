import unittest

from streamlink.plugins.willax import Willax


class TestPluginWillax(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://willax.tv/en-vivo/',
        ]
        for url in should_match:
            self.assertTrue(Willax.can_handle_url(url), url)

    def test_can_handle_url_negative(self):
        should_not_match = [
            'http://willax.tv/',
        ]
        for url in should_not_match:
            self.assertFalse(Willax.can_handle_url(url), url)
