import unittest

from streamlink.plugins.canalplus import CanalPlus


class TestPluginCanalPlus(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(CanalPlus.can_handle_url("https://www.mycanal.fr/docus-infos/l-info-du-vrai-du-13-12-politique-les-affaires-reprennent/p/1473830"))
        self.assertTrue(CanalPlus.can_handle_url("https://www.mycanal.fr/sport/infosport-laurey-et-claudia/p/1473752"))
        self.assertTrue(CanalPlus.can_handle_url("https://www.mycanal.fr/docus-infos/ses-debuts-a-madrid-extrait-le-k-benzema/p/1469050"))
        self.assertTrue(CanalPlus.can_handle_url("https://www.mycanal.fr/d8-docs-mags/au-revoir-johnny-hallyday-le-doc/p/1473054"))
        self.assertTrue(CanalPlus.can_handle_url("http://www.cnews.fr/direct"))
        self.assertTrue(CanalPlus.can_handle_url("http://www.cnews.fr/politique/video/des-electeurs-toujours-autant-indecis-174769"))
        self.assertTrue(CanalPlus.can_handle_url("http://www.cnews.fr/magazines/plus-de-recul/de-recul-du-14042017-174594"))
        # shouldn't match
        self.assertFalse(CanalPlus.can_handle_url("http://www.canalplus.fr/"))
        self.assertFalse(CanalPlus.can_handle_url("http://www.c8.fr/"))
        self.assertFalse(CanalPlus.can_handle_url("http://replay.c8.fr/"))
        self.assertFalse(CanalPlus.can_handle_url("http://www.cstar.fr/"))
        self.assertFalse(CanalPlus.can_handle_url("http://replay.cstar.fr/"))
        self.assertFalse(CanalPlus.can_handle_url("http://www.cnews.fr/"))
        self.assertFalse(CanalPlus.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(CanalPlus.can_handle_url("http://www.youtube.com/"))
