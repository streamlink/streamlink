import unittest

from streamlink.plugins.rtve import Rtve


class TestPluginRtve(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://www.rtve.es/directo/la-1',
            'http://www.rtve.es/directo/la-2/',
            'http://www.rtve.es/directo/teledeporte/',
            'http://www.rtve.es/directo/canal-24h/',
        ]
        for url in should_match:
            self.assertTrue(Rtve.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://www.rtve.es',
        ]
        for url in should_not_match:
            self.assertFalse(Rtve.can_handle_url(url))
