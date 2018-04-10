import unittest

from streamlink.plugins.tvp import TVP


class TestPluginTVP(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://tvpstream.vod.tvp.pl/?channel_id=14327511',
            'http://tvpstream.vod.tvp.pl/?channel_id=1455',
        ]
        for url in should_match:
            self.assertTrue(TVP.can_handle_url(url))

        should_not_match = [
            'http://tvp.pl/',
            'http://vod.tvp.pl/',
        ]
        for url in should_not_match:
            self.assertFalse(TVP.can_handle_url(url))
