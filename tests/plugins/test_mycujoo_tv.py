import unittest

from streamlink.plugins.mycujoo_tv import MycujooTv


class TestPluginMycujooTv(unittest.TestCase):
    def test_can_handle_url(self):
        self.assertTrue(MycujooTv.can_handle_url("https://mycujoo.tv/video/example?id=123"))
        self.assertTrue(MycujooTv.can_handle_url("http://mycujoo.tv/video/example?id=123"))
        self.assertTrue(MycujooTv.can_handle_url("https://mycujoo.tv/video/example?vid=123"))
        self.assertTrue(MycujooTv.can_handle_url("http://mycujoo.tv/video/example?vid=123"))
        self.assertTrue(MycujooTv.can_handle_url("https://mycujoo.tv/video/example"))
        self.assertTrue(MycujooTv.can_handle_url("http://mycujoo.tv/video/example"))
        self.assertTrue(MycujooTv.can_handle_url("https://mycujoo.tv/video/exa-mple"))
        self.assertTrue(MycujooTv.can_handle_url("http://mycujoo.tv/video/exa-mple"))

    def test_can_handle_url_negative(self):
        self.assertFalse(MycujooTv.can_handle_url("https://mycujoo.tv/"))
        self.assertFalse(MycujooTv.can_handle_url("http://mycujoo.tv/"))
        self.assertFalse(MycujooTv.can_handle_url("https://mycujoo.tv/other-site/"))
        self.assertFalse(MycujooTv.can_handle_url("http://mycujoo.tv/other-site/"))
        self.assertFalse(MycujooTv.can_handle_url("https://mycujoo.tv/video"))
        self.assertFalse(MycujooTv.can_handle_url("http://mycujoo.tv/video"))
        self.assertFalse(MycujooTv.can_handle_url("https://mycujoo.tv/video/"))
        self.assertFalse(MycujooTv.can_handle_url("http://mycujoo.tv/video/"))
