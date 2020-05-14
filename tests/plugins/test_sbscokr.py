import unittest

from streamlink.plugins.sbscokr import SBScokr


class TestPluginSBScokr(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://play.sbs.co.kr/onair/pc/index.html',
            'http://play.sbs.co.kr/onair/pc/index.html',
        ]
        for url in should_match:
            self.assertTrue(SBScokr.can_handle_url(url))

        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(SBScokr.can_handle_url(url))
