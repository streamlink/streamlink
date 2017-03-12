import unittest

from streamlink.plugins.canlitv import Canlitv


class TestPluginCanlitv(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Canlitv.can_handle_url("http://www.canlitv.com/channel"))
        self.assertTrue(Canlitv.can_handle_url("http://www.canlitv.life/channel"))
        self.assertTrue(Canlitv.can_handle_url("http://www.canlitvlive.co/izle/channel.html"))
        self.assertTrue(Canlitv.can_handle_url("http://www.canlitvlive.live/izle/channel.html"))
        self.assertTrue(Canlitv.can_handle_url("http://www.ecanlitvizle.net/channel/"))
        self.assertTrue(Canlitv.can_handle_url("http://www.ecanlitvizle.net/onizleme.php?kanal=channel"))
        self.assertTrue(Canlitv.can_handle_url("http://www.ecanlitvizle.net/tv.php?kanal=channel"))
        # shouldn't match
        self.assertFalse(Canlitv.can_handle_url("http://www.canlitv.com"))
        self.assertFalse(Canlitv.can_handle_url("http://www.ecanlitvizle.net"))
