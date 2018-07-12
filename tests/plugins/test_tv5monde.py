import unittest

from streamlink.plugins.tv5monde import TV5Monde


class TestPluginTV5Monde(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(TV5Monde.can_handle_url("http://live.tv5monde.com/fbs.html"))
        self.assertTrue(TV5Monde.can_handle_url("http://information.tv5monde.com/les-jt/monde"))
        self.assertTrue(TV5Monde.can_handle_url("http://information.tv5monde.com/info/legislatives-en-france-carnet-de-campagne-a-montreal-172631"))
        self.assertTrue(TV5Monde.can_handle_url("http://www.tv5mondeplusafrique.com/video_karim_ben_khelifa_je_ne_suis_pas_votre_negre_oumou_sangare_4658602.html"))
        self.assertTrue(TV5Monde.can_handle_url("http://www.tv5mondeplus.com/toutes-les-videos/information/tv5monde-le-journal-edition-du-02-06-17-11h00"))
        self.assertTrue(TV5Monde.can_handle_url("http://focus.tv5monde.com/prevert/le-roi-et-loiseau/"))

        # shouldn't match
        self.assertFalse(TV5Monde.can_handle_url("http://www.tv5.ca/"))
        self.assertFalse(TV5Monde.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(TV5Monde.can_handle_url("http://www.youtube.com/"))
