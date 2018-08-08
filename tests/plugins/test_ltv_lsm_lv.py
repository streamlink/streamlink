import unittest

from streamlink.plugins.ltv_lsm_lv import LtvLsmLv


class TestPluginLtvLsmLv(unittest.TestCase):
    def test_can_handle_url(self):
        self.assertTrue(LtvLsmLv.can_handle_url("https://ltv.lsm.lv/lv/tieshraide/example/"))
        self.assertTrue(LtvLsmLv.can_handle_url("http://ltv.lsm.lv/lv/tieshraide/example/"))
        self.assertTrue(LtvLsmLv.can_handle_url("https://ltv.lsm.lv/lv/tieshraide/example/live.123/"))
        self.assertTrue(LtvLsmLv.can_handle_url("http://ltv.lsm.lv/lv/tieshraide/example/live.123/"))

    def test_can_handle_url_negative(self):
        self.assertFalse(LtvLsmLv.can_handle_url("https://ltv.lsm.lv"))
        self.assertFalse(LtvLsmLv.can_handle_url("http://ltv.lsm.lv"))
        self.assertFalse(LtvLsmLv.can_handle_url("https://ltv.lsm.lv/lv"))
        self.assertFalse(LtvLsmLv.can_handle_url("http://ltv.lsm.lv/lv"))
        self.assertFalse(LtvLsmLv.can_handle_url("https://ltv.lsm.lv/other-site/"))
        self.assertFalse(LtvLsmLv.can_handle_url("http://ltv.lsm.lv/other-site/"))
        self.assertFalse(LtvLsmLv.can_handle_url("https://ltv.lsm.lv/lv/other-site/"))
        self.assertFalse(LtvLsmLv.can_handle_url("http://ltv.lsm.lv/lv/other-site/"))
