import unittest

from streamlink.plugins.tlctr import TLCtr


class TestPluginTLCtr(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.tlctv.com.tr/canli-izle',
        ]
        for url in should_match:
            self.assertTrue(TLCtr.can_handle_url(url))

        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(TLCtr.can_handle_url(url))
