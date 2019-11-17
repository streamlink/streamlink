import unittest

from streamlink.plugins.nhltv import NHLTV


class TestPluginNHLTV(unittest.TestCase):

    def test_can_handle_url(self):
        should_match = [
            'https://www.nhl.com/tv/2019020308',
            'https://www.nhl.com/tv/2019020308/221-2003761',
            'https://www.nhl.com/tv/2019020308/221-2003761/69949703',
            'https://www.nhl.com/tv/2019020308/221-2003761/69949703#game=2019020308,tfs=20191117_000000',
        ]
        for url in should_match:
            self.assertTrue(NHLTV.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(NHLTV.can_handle_url(url))
