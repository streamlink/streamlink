import unittest

from streamlink.plugins.googledrive import GoogleDocs


class TestPluginGoogleDocs(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://drive.google.com/file/d/123123/preview?start=1',
        ]
        for url in should_match:
            self.assertTrue(GoogleDocs.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(GoogleDocs.can_handle_url(url))
