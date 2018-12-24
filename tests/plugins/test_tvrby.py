import unittest

from streamlink.plugins.tvrby import TVRBy


class TestPluginTVRBy(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(TVRBy.can_handle_url("https://www.tvr.by/plugines/online-tv-main.php?channel=tv&chan_id=bt1"))
        self.assertTrue(TVRBy.can_handle_url("https://www.tvr.by/plugines/online-tv-main.php?channel=tv&chan_id=bt2"))
        self.assertTrue(TVRBy.can_handle_url("https://www.tvr.by/plugines/online-tv-main.php?channel=tv&chan_id=bt3"))
        self.assertTrue(TVRBy.can_handle_url("https://www.tvr.by/plugines/online-tv-main.php?channel=tv&chan_id=bt5"))

        # shouldn't match
        self.assertFalse(TVRBy.can_handle_url("http://www.tv8.cat/algo/"))
        self.assertFalse(TVRBy.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(TVRBy.can_handle_url("http://www.youtube.com/"))


