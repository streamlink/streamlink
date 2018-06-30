import unittest

from streamlink.plugins.media_ccc_de import media_ccc_de


class TestPluginmedia_ccc_de(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://media.ccc.de/path/to/talk.html',
            'https://streaming.media.ccc.de/room/',
        ]
        for url in should_match:
            self.assertTrue(media_ccc_de.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(media_ccc_de.can_handle_url(url))
