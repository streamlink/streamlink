import unittest

from streamlink.plugins.canalplus import CanalPlus


class TestPluginCanalPlus(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "https://www.mycanal.fr/docus-infos/l-info-du-vrai-du-13-12-politique-les-affaires-reprennent/p/1473830",
            "https://www.mycanal.fr/sport/infosport-laurey-et-claudia/p/1473752",
            "https://www.mycanal.fr/docus-infos/ses-debuts-a-madrid-extrait-le-k-benzema/p/1469050",
            "https://www.mycanal.fr/d8-docs-mags/au-revoir-johnny-hallyday-le-doc/p/1473054"
        ]
        for url in should_match:
            self.assertTrue(CanalPlus.can_handle_url(url))

        should_not_match = [
            "http://www.cnews.fr/direct",
            "http://www.cnews.fr/politique/video/des-electeurs-toujours-autant-indecis-174769",
            "http://www.cnews.fr/magazines/plus-de-recul/de-recul-du-14042017-174594",
            "http://www.canalplus.fr/",
            "http://www.c8.fr/",
            "http://replay.c8.fr/",
            "http://www.cstar.fr/",
            "http://replay.cstar.fr/",
            "http://www.cnews.fr/",
            "http://www.tvcatchup.com/",
            "http://www.youtube.com/"
        ]
        for url in should_not_match:
            self.assertFalse(CanalPlus.can_handle_url(url))
