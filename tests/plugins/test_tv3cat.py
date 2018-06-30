import unittest

from streamlink.plugins.tv3cat import TV3Cat


class TestPluginTV3Cat(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://www.ccma.cat/tv3/directe/tv3/',
            'http://www.ccma.cat/tv3/directe/324/',
        ]
        for url in should_match:
            self.assertTrue(TV3Cat.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(TV3Cat.can_handle_url(url))
