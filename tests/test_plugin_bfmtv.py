import unittest

from streamlink.plugins.bfmtv import BFMTV


class TestPluginBFMTV(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(BFMTV.can_handle_url("http://www.bfmtv.com/mediaplayer/live-video/"))
        self.assertTrue(BFMTV.can_handle_url("http://bfmbusiness.bfmtv.com/mediaplayer/live-video/"))
        self.assertTrue(BFMTV.can_handle_url("http://www.bfmtv.com/mediaplayer/live-bfm-paris/"))
        self.assertTrue(BFMTV.can_handle_url("http://rmc.bfmtv.com/mediaplayer/live-audio/"))
        self.assertTrue(BFMTV.can_handle_url("http://rmcsport.bfmtv.com/mediaplayer/live-bfm-sport/"))
        self.assertTrue(BFMTV.can_handle_url("http://rmcdecouverte.bfmtv.com/mediaplayer-direct/"))
        self.assertTrue(BFMTV.can_handle_url("http://www.bfmtv.com/mediaplayer/replay/premiere-edition/"))
        self.assertTrue(BFMTV.can_handle_url("http://bfmbusiness.bfmtv.com/mediaplayer/replay/good-morning-business/"))
        self.assertTrue(BFMTV.can_handle_url("http://rmc.bfmtv.com/mediaplayer/replay/les-grandes-gueules/"))
        self.assertTrue(BFMTV.can_handle_url("http://rmcdecouverte.bfmtv.com/mediaplayer-replay/?id=6714&title=TOP%20GEAR%20:PASSION%20VINTAGE"))
        self.assertTrue(BFMTV.can_handle_url("http://rmc.bfmtv.com/mediaplayer/replay/after-foot/"))
        self.assertTrue(BFMTV.can_handle_url("http://www.01net.com/mediaplayer/replay/jtech/"))
        self.assertTrue(BFMTV.can_handle_url("http://www.bfmtv.com/politique/macron-et-le-pen-talonnes-par-fillon-et-melenchon-a-l-approche-du-premier-tour-1142070.html"))

        # shouldn't match
        self.assertFalse(BFMTV.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(BFMTV.can_handle_url("http://www.youtube.com/"))
