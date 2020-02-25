import unittest

from streamlink.plugins.gulli import Gulli


class TestPluginGulli(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "http://replay.gulli.fr/Direct",
            "http://replay.gulli.fr/dessins-animes/My-Little-Pony-les-amies-c-est-magique/VOD68328764799000",
            "https://replay.gulli.fr/emissions/In-Ze-Boite2/VOD68639028668000",
            "https://replay.gulli.fr/series/Power-Rangers-Dino-Super-Charge/VOD68612908435000"
        ]
        for url in should_match:
            self.assertTrue(Gulli.can_handle_url(url))

        should_not_match = [
            "http://replay.gulli.fr/",
            "http://replay.gulli.fr/dessins-animes",
            "http://replay.gulli.fr/emissions",
            "http://replay.gulli.fr/series",
            "http://www.tvcatchup.com/",
            "http://www.youtube.com/"
        ]
        for url in should_not_match:
            self.assertFalse(Gulli.can_handle_url(url))
