import unittest

from streamlink.plugins.nbcsports import NBCSports


class TestPluginNBCSports(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.nbcsports.com/video/evertons-wayne-rooney-completes-hat-trick-goal-midfield',
        ]
        for url in should_match:
            self.assertTrue(NBCSports.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(NBCSports.can_handle_url(url))
