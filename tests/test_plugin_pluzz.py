import unittest

from streamlink.plugins.pluzz import Pluzz


class TestPluginPluzz(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Pluzz.can_handle_url("https://www.france.tv/france-2/direct.html"))
        self.assertTrue(Pluzz.can_handle_url("https://www.france.tv/france-3/direct.html"))
        self.assertTrue(Pluzz.can_handle_url("https://www.france.tv/france-3-franche-comte/direct.html"))
        self.assertTrue(Pluzz.can_handle_url("https://www.france.tv/france-4/direct.html"))
        self.assertTrue(Pluzz.can_handle_url("https://www.france.tv/france-5/direct.html"))
        self.assertTrue(Pluzz.can_handle_url("https://www.france.tv/france-o/direct.html"))
        self.assertTrue(Pluzz.can_handle_url("https://www.france.tv/franceinfo/direct.html"))
        self.assertTrue(Pluzz.can_handle_url("https://www.france.tv/france-2/journal-20h00/141003-edition-du-lundi-8-mai-2017.html"))
        self.assertTrue(Pluzz.can_handle_url("https://www.france.tv/france-o/underground/saison-1/132187-underground.html"))
        self.assertTrue(Pluzz.can_handle_url("http://www.ludo.fr/heros/the-batman"))
        self.assertTrue(Pluzz.can_handle_url("http://www.ludo.fr/heros/il-etait-une-fois-la-vie"))
        self.assertTrue(Pluzz.can_handle_url("http://www.zouzous.fr/heros/oui-oui"))
        self.assertTrue(Pluzz.can_handle_url("http://www.zouzous.fr/heros/marsupilami-1"))
        self.assertTrue(Pluzz.can_handle_url("http://france3-regions.francetvinfo.fr/bourgogne-franche-comte/tv/direct/franche-comte"))
        self.assertTrue(Pluzz.can_handle_url("http://sport.francetvinfo.fr/roland-garros/direct"))
        self.assertTrue(Pluzz.can_handle_url("http://sport.francetvinfo.fr/roland-garros/live-court-3"))
        self.assertTrue(Pluzz.can_handle_url("http://sport.francetvinfo.fr/roland-garros/andy-murray-gbr-1-andrey-kuznetsov-rus-1er-tour-court-philippe-chatrier"))

        # shouldn't match
        self.assertFalse(Pluzz.can_handle_url("http://www.france.tv/"))
        self.assertFalse(Pluzz.can_handle_url("http://pluzz.francetv.fr/"))
        self.assertFalse(Pluzz.can_handle_url("http://www.ludo.fr/"))
        self.assertFalse(Pluzz.can_handle_url("http://www.ludo.fr/jeux"))
        self.assertFalse(Pluzz.can_handle_url("http://www.zouzous.fr/"))
        self.assertFalse(Pluzz.can_handle_url("http://france3-regions.francetvinfo.fr/"))
        self.assertFalse(Pluzz.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(Pluzz.can_handle_url("http://www.youtube.com/"))
