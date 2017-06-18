import sys

from streamlink.plugins.adultswim import AdultSwim
if sys.version_info[0:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest


class TestPluginAdultSwim(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(AdultSwim.can_handle_url("http://www.adultswim.com/videos/streams/toonami"))
        self.assertTrue(AdultSwim.can_handle_url("http://www.adultswim.com/videos/streams/"))
        self.assertTrue(AdultSwim.can_handle_url("http://www.adultswim.com/videos/streams/last-stream-on-the-left"))
        self.assertTrue(AdultSwim.can_handle_url("http://www.adultswim.com/videos/specials/the-adult-swim-golf-classic-extended/"))
        self.assertTrue(AdultSwim.can_handle_url("http://www.adultswim.com/videos/streams/toonami-pre-flight/friday-december-30th-2016"))

        # shouldn't match
        self.assertFalse(AdultSwim.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(AdultSwim.can_handle_url("http://www.youtube.com/"))

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
