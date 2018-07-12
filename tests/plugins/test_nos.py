import unittest

from streamlink.plugins.nos import NOS


class TestPluginNOS(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://nos.nl/livestream/2220100-wk-sprint-schaatsen-1-000-meter-mannen.html',
        ]
        for url in should_match:
            self.assertTrue(NOS.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(NOS.can_handle_url(url))
