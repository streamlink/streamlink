import unittest

from streamlink.plugins.dash import MPEGDASH


class TestPluginMPEGDASH(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(MPEGDASH.can_handle_url("http://example.com/fpo.mpd"))
        self.assertTrue(MPEGDASH.can_handle_url("dash://http://www.testing.cat/directe"))
        self.assertTrue(MPEGDASH.can_handle_url("dash://https://www.testing.cat/directe"))

    def test_can_handle_url_negative(self):
        # shouldn't match
        self.assertFalse(MPEGDASH.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(MPEGDASH.can_handle_url("http://www.youtube.com/"))
