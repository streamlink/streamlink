import unittest

from streamlink.plugins.nimotv import NimoTV


class TestPluginNimoTV(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://www.nimo.tv/live/737614',
            'https://www.nimo.tv/live/737614',
            'http://www.nimo.tv/sanz',
            'https://www.nimo.tv/sanz',
        ]
        for url in should_match:
            self.assertTrue(NimoTV.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(NimoTV.can_handle_url(url))
