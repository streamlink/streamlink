import unittest

from streamlink.plugins.foxtr import FoxTR


class TestPluginFoxTR(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://www.fox.com.tr/canli-yayin',
        ]
        for url in should_match:
            self.assertTrue(FoxTR.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(FoxTR.can_handle_url(url))
