import unittest

from streamlink.plugins.showroom import Showroom

_should_match = (
    "https://www.showroom-live.com/48_NISHIMURA_NANAKO",
    "https://www.showroom-live.com/room/profile?room_id=61734",
    "http://showroom-live.com/48_YAMAGUCHI_MAHO",
    "https://www.showroom-live.com/4b9581094890",
    "https://www.showroom-live.com/157941217780",
    "https://www.showroom-live.com/madokacom"
)
_should_not_match = (
    "https://www.showroom-live.com/mypage",
    "https://www.showroom-live.com/ranking",
    "https://www.showroom-live.com/payment/payment_start",
    "https://www.showroom-live.com/s/licence",
    "http://www.youtube.com/",
    "http://www.dailymotion.com/video/x5cyk8f",
    "http://www.crunchyroll.com/gintama"
)
_stream_weights = {
    'high': (720, "quality"),
    'other': (360, "quality"),
    'low': (160, "quality")
}


class TestPluginShowroom(unittest.TestCase):
    def test_can_handle_url(self):
        for url in _should_match:
            self.assertTrue(Showroom.can_handle_url(url))

        for url in _should_not_match:
            self.assertFalse(Showroom.can_handle_url(url))

    def test_stream_weight(self):
        for name, weight in _stream_weights.items():
            self.assertEqual(Showroom.stream_weight(name), weight)
