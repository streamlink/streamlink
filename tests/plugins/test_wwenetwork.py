import unittest

from streamlink.plugins.wwenetwork import WWENetwork


class TestPluginWWENetwork(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://network.wwe.com/shows/collections/267406022',
        ]
        for url in should_match:
            self.assertTrue(WWENetwork.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(WWENetwork.can_handle_url(url))
