import unittest

from streamlink.plugins.ine import INE


class TestPluginINE(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://streaming.ine.com/play/11111111-2222-3333-4444-555555555555/introduction/',
        ]
        for url in should_match:
            self.assertTrue(INE.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(INE.can_handle_url(url))
