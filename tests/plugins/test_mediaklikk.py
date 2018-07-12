import unittest

from streamlink.plugins.mediaklikk import Mediaklikk


class TestPluginMediaklikk(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.mediaklikk.hu/duna-world-elo/',
            'https://www.mediaklikk.hu/duna-world-radio-elo',
            'https://www.mediaklikk.hu/m1-elo',
            'https://www.mediaklikk.hu/m2-elo',
        ]
        for url in should_match:
            self.assertTrue(Mediaklikk.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://www.mediaklikk.hu',
        ]
        for url in should_not_match:
            self.assertFalse(Mediaklikk.can_handle_url(url))
