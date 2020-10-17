import unittest

from streamlink.plugins.attheshore import AtTheShore


class TestPluginAtTheShore(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "http://attheshore.com/livecam-steelpier564",
        ]
        for url in should_match:
            self.assertTrue(AtTheShore.can_handle_url(url))

        should_not_match = [
            "http://attheshore.com/livecams",
            "http://www.youtube.com/",

        ]
        for url in should_not_match:
            self.assertFalse(AtTheShore.can_handle_url(url))
