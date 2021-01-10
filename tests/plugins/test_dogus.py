import unittest

from streamlink.plugins.dogus import Dogus


class TestPluginDogus(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://eurostartv.com.tr/canli-izle',
            'http://kralmuzik.com.tr/tv/',
            'http://ntv.com.tr/canli-yayin/ntv',
            'http://startv.com.tr/canli-yayin',
        ]
        for url in should_match:
            self.assertTrue(Dogus.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
            'http://www.ntvspor.net/canli-yayin',
        ]
        for url in should_not_match:
            self.assertFalse(Dogus.can_handle_url(url))
