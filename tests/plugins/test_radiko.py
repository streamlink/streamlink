import unittest

from streamlink.plugins.radiko import Radiko


class TestPluginRadiko(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://radiko.jp/#!/live/QRR',
            'https://radiko.jp/#!/ts/YFM/20201206010000',
            'http://radiko.jp/#!/live/QRR',
            'http://radiko.jp/live/QRR',
            'http://radiko.jp/#!/ts/QRR/20200308180000',
            'http://radiko.jp/ts/QRR/20200308180000'
        ]
        for url in should_match:
            self.assertTrue(Radiko.can_handle_url(url), url)

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Radiko.can_handle_url(url), url)
