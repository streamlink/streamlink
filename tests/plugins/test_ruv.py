import unittest

from streamlink.plugins.ruv import Ruv


class TestPluginRuv(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "ruv.is/ruv",
            "http://ruv.is/ruv",
            "http://ruv.is/ruv/",
            "https://ruv.is/ruv/",
            "http://www.ruv.is/ruv",
            "http://www.ruv.is/ruv/",
            "ruv.is/ruv2",
            "ruv.is/ras1",
            "ruv.is/ras2",
            "ruv.is/rondo",
            "http://www.ruv.is/spila/ruv/ol-2018-ishokki-karla/20180217",
            "http://www.ruv.is/spila/ruv/frettir/20180217"
        ]
        for url in should_match:
            self.assertTrue(Ruv.can_handle_url(url))

        should_not_match = [
            "rruv.is/ruv",
            "ruv.is/ruvnew",
            "https://www.bloomberg.com/live/",
            "https://www.bloomberg.com/politics/articles/2017-04-17/french-race-up-for-grabs-days-before-voters"
            + "-cast-first-ballots",
            "http://www.tvcatchup.com/",
            "http://www.youtube.com/"
        ]
        for url in should_not_match:
            self.assertFalse(Ruv.can_handle_url(url))
