import unittest

from streamlink.plugins.vinhlongtv import VinhLongTV


class TestPluginVinhLongTV(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://thvli.vn/live/thvl1-hd/aab94d1f-44e1-4992-8633-6d46da08db42',
            'http://thvli.vn/live/thvl2-hd/bc60bddb-99ac-416e-be26-eb4d0852f5cc',
            'http://thvli.vn/live/phat-thanh/c87174ba-7aeb-4cb4-af95-d59de715464c',
        ]
        for url in should_match:
            self.assertTrue(VinhLongTV.can_handle_url(url))

        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(VinhLongTV.can_handle_url(url))
