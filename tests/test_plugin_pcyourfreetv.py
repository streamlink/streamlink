import unittest

from streamlink.plugins.pcyourfreetv import PCYourFreeTV


class TestPluginPCYourFreeTV(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(PCYourFreeTV.can_handle_url("http://pc-yourfreetv.com/indexplayer.php?channel=das%20erste&page_id=41"))
        self.assertTrue(PCYourFreeTV.can_handle_url("http://pc-yourfreetv.com/indexplayer.php?channel=srf%20eins&page_id=41"))
        self.assertTrue(PCYourFreeTV.can_handle_url("http://pc-yourfreetv.com/indexplayer.php?channel=bbc%20one&page_id=41"))
        self.assertTrue(PCYourFreeTV.can_handle_url("http://pc-yourfreetv.com/indexplayer.php?channel=tf1&page_id=41"))

        # shouldn't match
        self.assertFalse(PCYourFreeTV.can_handle_url("http://pc-yourfreetv.com/home.php"))
        self.assertFalse(PCYourFreeTV.can_handle_url("http://pc-yourfreetv.com/indexlivetv.php?page_id=1"))
        self.assertFalse(PCYourFreeTV.can_handle_url("http://tvcatchup.com/"))
        self.assertFalse(PCYourFreeTV.can_handle_url("http://youtube.com/"))
