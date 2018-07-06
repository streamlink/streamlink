import unittest

from streamlink.plugins.rtvs import Rtvs


class TestPluginRtvs(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://www.rtvs.sk/televizia/live-1',
            'http://www.rtvs.sk/televizia/live-2',
            'http://www.rtvs.sk/televizia/live-o',
        ]
        for url in should_match:
            self.assertTrue(Rtvs.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'http://www.rtvs.sk/',
        ]
        for url in should_not_match:
            self.assertFalse(Rtvs.can_handle_url(url))
