import unittest

from streamlink.plugins.mico import Mico


class TestPluginMico(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://micous.com/live/73750760',
            'http://www.micous.com/live/73750760',
            'https://micous.com/live/73750760',
            'https://www.micous.com/live/73750760',
        ]
        for url in should_match:
            self.assertTrue(Mico.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'http://www.micous.com/73750760',
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Mico.can_handle_url(url))
