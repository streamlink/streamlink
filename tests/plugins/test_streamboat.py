import unittest

from streamlink.plugins.streamboat import StreamBoat


class TestPluginStreamBoat(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://streamboat.tv/@example',
            'https://streamboat.tv/@test',
        ]
        for url in should_match:
            self.assertTrue(StreamBoat.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(StreamBoat.can_handle_url(url))
