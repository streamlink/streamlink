import unittest

from streamlink.plugins.showroom import Showroom
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlShowroom(PluginCanHandleUrl):
    __plugin__ = Showroom

    should_match = [
        "https://www.showroom-live.com/48_NISHIMURA_NANAKO",
        "https://www.showroom-live.com/room/profile?room_id=61734",
        "http://showroom-live.com/48_YAMAGUCHI_MAHO",
        "https://www.showroom-live.com/4b9581094890",
        "https://www.showroom-live.com/157941217780",
        "https://www.showroom-live.com/madokacom"
    ]

    should_not_match = [
        "https://www.showroom-live.com/payment/payment_start",
        "https://www.showroom-live.com/s/licence",
    ]


class TestPluginShowroom(unittest.TestCase):
    stream_weights = {
        'high': (720, "quality"),
        'other': (360, "quality"),
        'low': (160, "quality")
    }

    def test_stream_weight(self):
        for name, weight in self.stream_weights.items():
            self.assertEqual(Showroom.stream_weight(name), weight)
