import unittest

from streamlink.plugins.canalplus import CanalPlus


class TestPluginCanalPlus(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(CanalPlus.can_handle_url("http://www.canalplus.fr/pid3580-live-tv-clair.html"))
        self.assertTrue(CanalPlus.can_handle_url("http://www.canalplus.fr/emissions/pid8596-the-tonight-show.html"))
        self.assertTrue(CanalPlus.can_handle_url("http://www.canalplus.fr/c-divertissement/pid1787-c-groland.html?vid=1430239"))
        self.assertTrue(CanalPlus.can_handle_url("http://www.c8.fr/pid5323-c8-live.html"))
        self.assertTrue(CanalPlus.can_handle_url("http://www.c8.fr/c8-divertissement/pid8758-c8-la-folle-histoire-de-sophie-marceau.html"))
        self.assertTrue(CanalPlus.can_handle_url("http://www.c8.fr/c8-sport/pid5224-c8-direct-auto.html?vid=1430292"))
        self.assertTrue(CanalPlus.can_handle_url("http://replay.c8.fr/video/1431076"))
        self.assertTrue(CanalPlus.can_handle_url("http://www.cstar.fr/pid5322-cstar-live.html"))
        self.assertTrue(CanalPlus.can_handle_url("http://www.cstar.fr/emissions/pid8754-wild-transport.html"))
        self.assertTrue(CanalPlus.can_handle_url("http://www.cstar.fr/musique/pid6282-les-tops.html?vid=1430143"))
        self.assertTrue(CanalPlus.can_handle_url("http://replay.cstar.fr/video/1430245"))

        # shouldn't match
        self.assertFalse(CanalPlus.can_handle_url("http://www.canalplus.fr/"))
        self.assertFalse(CanalPlus.can_handle_url("http://www.c8.fr/"))
        self.assertFalse(CanalPlus.can_handle_url("http://replay.c8.fr/"))
        self.assertFalse(CanalPlus.can_handle_url("http://www.cstar.fr/"))
        self.assertFalse(CanalPlus.can_handle_url("http://replay.cstar.fr/"))
        self.assertFalse(CanalPlus.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(CanalPlus.can_handle_url("http://www.youtube.com/"))
