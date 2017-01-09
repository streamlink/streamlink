import unittest

from streamlink.plugins.bnt import BNT


class TestPluginBNT(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(BNT.can_handle_url("http://bgonair.bg/tvonline"))
        self.assertTrue(BNT.can_handle_url("http://bgonair.bg/tvonline/"))
        self.assertTrue(BNT.can_handle_url("http://bitelevision.com/live"))
        self.assertTrue(BNT.can_handle_url("http://www.kanal3.bg/live"))
        self.assertTrue(BNT.can_handle_url("http://www.nova.bg/live"))
        self.assertTrue(BNT.can_handle_url("http://nova.bg/live"))
        self.assertTrue(BNT.can_handle_url("http://tv.bnt.bg/bntworld/"))
        self.assertTrue(BNT.can_handle_url("http://tv.bnt.bg/bnt1/hd/"))
        self.assertTrue(BNT.can_handle_url("http://tv.bnt.bg/bnt1/hd"))
        self.assertTrue(BNT.can_handle_url("http://tv.bnt.bg/bnt1/16x9/"))
        self.assertTrue(BNT.can_handle_url("http://tv.bnt.bg/bnt1/16x9"))
        self.assertTrue(BNT.can_handle_url("http://tv.bnt.bg/bnt2/16x9/"))
        self.assertTrue(BNT.can_handle_url("http://tv.bnt.bg/bnt2/16x9"))

        # shouldn't match
        self.assertFalse(BNT.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(BNT.can_handle_url("http://www.youtube.com/"))
