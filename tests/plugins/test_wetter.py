import unittest

from streamlink.plugins.wetter import Wetter


class TestPluginWetter(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "https://wetter.com/hd-live-webcams/kroatien/panorama-split-webcam-riva/5c81ccdea5b4b9130764ead8/",
            "http://www.wetter.com/hd-live-webcams/deutschland/hamburg-elbe/5152d06034178/",
        ]
        for url in should_match:
            self.assertTrue(Wetter.can_handle_url(url))

        should_not_match = [
            "http://www.youtube.com/",

        ]
        for url in should_not_match:
            self.assertFalse(Wetter.can_handle_url(url))
