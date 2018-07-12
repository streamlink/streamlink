import unittest

from streamlink.plugins.streamingvideoprovider import Streamingvideoprovider


class TestPluginStreamingvideoprovider(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://www.streamingvideoprovider.co.uk/example',
        ]
        for url in should_match:
            self.assertTrue(Streamingvideoprovider.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Streamingvideoprovider.can_handle_url(url))
