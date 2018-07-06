import unittest

from streamlink.plugins.periscope import Periscope


class TestPluginPeriscope(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.periscope.tv/Pac12Networks/1BdGYRLyzMyJX',
            'https://www.periscope.tv/w/1YqKDdaoVXLKV',
            'https://www.pscp.tv/Pac12Networks/1gqGvpPlVLlxB'
        ]
        for url in should_match:
            self.assertTrue(Periscope.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://www.periscope.tv/',
            'https://www.pscp.tv/',
        ]
        for url in should_not_match:
            self.assertFalse(Periscope.can_handle_url(url))
