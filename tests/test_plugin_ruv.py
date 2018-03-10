import unittest

from streamlink.plugins.ruv import Ruv


class TestPluginRuv(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Ruv.can_handle_url("ruv.is/ruv"))
        self.assertTrue(Ruv.can_handle_url("http://ruv.is/ruv"))
        self.assertTrue(Ruv.can_handle_url("http://ruv.is/ruv/"))
        self.assertTrue(Ruv.can_handle_url("https://ruv.is/ruv/"))
        self.assertTrue(Ruv.can_handle_url("http://www.ruv.is/ruv"))
        self.assertTrue(Ruv.can_handle_url("http://www.ruv.is/ruv/"))
        self.assertTrue(Ruv.can_handle_url("ruv.is/ruv2"))
        self.assertTrue(Ruv.can_handle_url("ruv.is/ras1"))
        self.assertTrue(Ruv.can_handle_url("ruv.is/ras2"))
        self.assertTrue(Ruv.can_handle_url("ruv.is/rondo"))
        self.assertTrue(Ruv.can_handle_url("http://www.ruv.is/spila/ruv/ol-2018-ishokki-karla/20180217"))
        self.assertTrue(Ruv.can_handle_url("http://www.ruv.is/spila/ruv/frettir/20180217"))

        # shouldn't match
        self.assertFalse(Ruv.can_handle_url("rruv.is/ruv"))
        self.assertFalse(Ruv.can_handle_url("ruv.is/ruvnew"))
        self.assertFalse(Ruv.can_handle_url("https://www.bloomberg.com/live/"))
        self.assertFalse(Ruv.can_handle_url("https://www.bloomberg.com/politics/articles/2017-04-17/french-race-up-for-grabs-days-before-voters-cast-first-ballots"))
        self.assertFalse(Ruv.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(Ruv.can_handle_url("http://www.youtube.com/"))
