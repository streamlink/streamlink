import unittest

from streamlink.plugins.zengatv import ZengaTV


class TestPluginZengaTV(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "http://www.zengatv.com/indiatoday.html",
            "http://www.zengatv.com/live/87021a6d-411e-11e2-b4c6-7071bccc85ac.html",
            "http://zengatv.com/indiatoday.html",
            "http://zengatv.com/live/87021a6d-411e-11e2-b4c6-7071bccc85ac.html",
        ]
        for url in should_match:
            self.assertTrue(ZengaTV.can_handle_url(url))

        should_not_match = [
            "http://www.zengatv.com",
            "http://www.zengatv.com/"
        ]
        for url in should_not_match:
            self.assertFalse(ZengaTV.can_handle_url(url))
