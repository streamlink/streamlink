import unittest

from streamlink.plugins.cdnbg import CDNBG


class TestPluginCDNBG(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(CDNBG.can_handle_url("http://bgonair.bg/tvonline"))
        self.assertTrue(CDNBG.can_handle_url("http://bgonair.bg/tvonline/"))
        self.assertTrue(CDNBG.can_handle_url("http://bitelevision.com/live"))
        self.assertTrue(CDNBG.can_handle_url("http://www.kanal3.bg/live"))
        self.assertTrue(CDNBG.can_handle_url("http://www.nova.bg/live"))
        self.assertTrue(CDNBG.can_handle_url("http://nova.bg/live"))
        self.assertTrue(CDNBG.can_handle_url("http://tv.bnt.bg/bntworld/"))
        self.assertTrue(CDNBG.can_handle_url("http://tv.bnt.bg/bnt1/hd/"))
        self.assertTrue(CDNBG.can_handle_url("http://tv.bnt.bg/bnt1/hd"))
        self.assertTrue(CDNBG.can_handle_url("http://tv.bnt.bg/bnt1/16x9/"))
        self.assertTrue(CDNBG.can_handle_url("http://tv.bnt.bg/bnt1/16x9"))
        self.assertTrue(CDNBG.can_handle_url("http://tv.bnt.bg/bnt2/16x9/"))
        self.assertTrue(CDNBG.can_handle_url("http://tv.bnt.bg/bnt2/16x9"))
        self.assertTrue(CDNBG.can_handle_url("http://inlife.bg/"))
        self.assertTrue(CDNBG.can_handle_url("https://mmtvmusic.com/live/"))
        self.assertTrue(CDNBG.can_handle_url("http://mu-vi.tv/LiveStreams/pages/Live.aspx"))
        self.assertTrue(CDNBG.can_handle_url("http://videochanel.bstv.bg/"))
        self.assertTrue(CDNBG.can_handle_url("http://live.bstv.bg/"))
        self.assertTrue(CDNBG.can_handle_url("https://www.bloombergtv.bg/video"))

        # shouldn't match
        self.assertFalse(CDNBG.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(CDNBG.can_handle_url("http://www.youtube.com/"))
        self.assertFalse(CDNBG.can_handle_url("https://www.tvevropa.com"))
