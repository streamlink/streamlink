import unittest

from streamlink.plugins.adultswim import AdultSwim


class TestPluginAdultSwim(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "http://www.adultswim.com/videos/streams/toonami",
            "http://www.adultswim.com/videos/streams/",
            "http://www.adultswim.com/videos/streams/last-stream-on-the-left",
            "http://www.adultswim.com/videos/specials/the-adult-swim-golf-classic-extended/",
            "http://www.adultswim.com/videos/streams/toonami-pre-flight/friday-december-30th-2016"
        ]
        for url in should_match:
            self.assertTrue(AdultSwim.can_handle_url(url))

        should_not_match = [
            "http://www.tvcatchup.com/",
            "http://www.youtube.com/"
        ]
        for url in should_not_match:
            self.assertFalse(AdultSwim.can_handle_url(url))

    def _test_regex(self, url, expected):
        m = AdultSwim.url_re.match(url)
        self.assertIsNotNone(m)
        self.assertListEqual(expected, list(m.groups()))

    def test_regex_live_stream(self):
        self._test_regex("http://www.adultswim.com/videos/streams/toonami",
                         ["streams", "toonami", None])

    def test_regex_live_stream_default(self):
        self._test_regex("http://www.adultswim.com/videos/streams/",
                         ["streams", None, None])

    def test_regex_special_vod(self):
        self._test_regex("http://www.adultswim.com/videos/specials/the-adult-swim-golf-classic-extended/",
                         [None, "specials", "the-adult-swim-golf-classic-extended"])

    def test_regex_live_replay(self):
        self._test_regex("http://www.adultswim.com/videos/streams/toonami-pre-flight/friday-december-30th-2016",
                         ["streams", "toonami-pre-flight", "friday-december-30th-2016"])

    def test_regex_show_vod(self):
        self._test_regex("http://www.adultswim.com/videos/aqua-teen-hunger-force/vampirus/",
                         [None, "aqua-teen-hunger-force", "vampirus"])
