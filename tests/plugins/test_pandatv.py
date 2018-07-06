import unittest

from streamlink.plugins.pandatv import Pandatv


class TestPluginPandatv(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.panda.tv/123123',
        ]
        for url in should_match:
            self.assertTrue(Pandatv.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Pandatv.can_handle_url(url))
