import unittest

from streamlink.plugins.canalplus import CanalPlus


class TestPluginCanalPlus(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(CanalPlus.can_handle_url("http://www.cnews.fr/le-direct"))
        self.assertTrue(CanalPlus.can_handle_url("http://www.cnews.fr/direct"))
        self.assertTrue(CanalPlus.can_handle_url("http://www.cnews.fr/politique/video/des-electeurs-toujours-autant-indecis-174769"))
        self.assertTrue(CanalPlus.can_handle_url("http://www.cnews.fr/magazines/plus-de-recul/de-recul-du-14042017-174594"))
        # shouldn't match
        self.assertFalse(CanalPlus.can_handle_url("http://www.cnews.fr/"))
        self.assertFalse(CanalPlus.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(CanalPlus.can_handle_url("http://www.youtube.com/"))
