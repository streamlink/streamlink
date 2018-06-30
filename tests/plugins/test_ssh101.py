import unittest

from streamlink.plugins.ssh101 import SSH101


class TestPluginSSH101(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://ssh101.com/live/sarggg',
        ]
        for url in should_match:
            self.assertTrue(SSH101.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(SSH101.can_handle_url(url))
