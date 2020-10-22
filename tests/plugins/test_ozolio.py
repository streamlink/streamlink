import unittest

from streamlink.plugins.ozolio import Ozolio


class TestPluginOzolio(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "http://ozolio.com/explore/",
            "https://www.ozolio.com/explore/WLWJ00000021",
        ]
        for url in should_match:
            self.assertTrue(Ozolio.can_handle_url(url))

        should_not_match = [
            "http://relay.ozolio.com/pub.api?cmd=avatar&oid=CID_XNQT0000099E",
            "http://www.youtube.com/",

        ]
        for url in should_not_match:
            self.assertFalse(Ozolio.can_handle_url(url))
