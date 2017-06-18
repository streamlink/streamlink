import unittest

from streamlink.plugins.gulli import Gulli


class TestPluginGulli(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Gulli.can_handle_url("http://replay.gulli.fr/Direct"))
        self.assertTrue(Gulli.can_handle_url("http://replay.gulli.fr/dessins-animes/My-Little-Pony-les-amies-c-est-magique/VOD68328764799000"))
        self.assertTrue(Gulli.can_handle_url("http://replay.gulli.fr/emissions/In-Ze-Boite2/VOD68639028668000"))
        self.assertTrue(Gulli.can_handle_url("http://replay.gulli.fr/series/Power-Rangers-Dino-Super-Charge/VOD68612908435000"))

        # shouldn't match
        self.assertFalse(Gulli.can_handle_url("http://replay.gulli.fr/"))
        self.assertFalse(Gulli.can_handle_url("http://replay.gulli.fr/dessins-animes"))
        self.assertFalse(Gulli.can_handle_url("http://replay.gulli.fr/emissions"))
        self.assertFalse(Gulli.can_handle_url("http://replay.gulli.fr/series"))
        self.assertFalse(Gulli.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(Gulli.can_handle_url("http://www.youtube.com/"))
