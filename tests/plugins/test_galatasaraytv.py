import unittest

from streamlink.plugins.galatasaraytv import GalatasarayTV


class TestPluginGalatasarayTV(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://galatasaray.com/',
            'https://galatasaray.com',
            'https://galatasaray.com/',
            'https://www.galatasaray.com/',
        ]
        for url in should_match:
            self.assertTrue(GalatasarayTV.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(GalatasarayTV.can_handle_url(url))
