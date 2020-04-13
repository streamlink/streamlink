import unittest

from streamlink.plugins.kugou import Kugou


class TestPluginKugou(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://fanxing.kugou.com/1062645?refer=605',
            'https://fanxing.kugou.com/77997777?refer=605',
            'https://fanxing.kugou.com/1047927?refer=605',
            'https://fanxing.kugou.com/1048570?refer=605',
            'https://fanxing.kugou.com/1062642?refer=605',
            'https://fanxing.kugou.com/1071651',
        ]
        for url in should_match:
            self.assertTrue(Kugou.can_handle_url(url), url)

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Kugou.can_handle_url(url), url)
