import unittest

from streamlink.plugins.onespotmedia import OneSpotmedia


class TestPluginOneSpotmedia(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.1spotmedia.com/#!/live-stream/79336998495',
            'https://www.1spotmedia.com/#!/live-stream/77999142467',
            'https://www.1spotmedia.com/#!/live-stream/79336998577',
            'https://www.1spotmedia.com/#!/live-stream/105260070736',
        ]
        for url in should_match:
            self.assertTrue(OneSpotmedia.can_handle_url(url), url)

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://www.1spotmedia.com',
        ]
        for url in should_not_match:
            self.assertFalse(OneSpotmedia.can_handle_url(url), url)
