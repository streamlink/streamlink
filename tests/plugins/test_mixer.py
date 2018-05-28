import unittest

from streamlink.plugins.mixer import Mixer


class TestPluginMixer(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Mixer.can_handle_url('https://mixer.com/Minecraft?vod=11250002'))
        self.assertTrue(Mixer.can_handle_url('https://mixer.com/Minecraft'))
        self.assertTrue(Mixer.can_handle_url('https://mixer.com/Monstercat?vod=11030270'))
        self.assertTrue(Mixer.can_handle_url('https://mixer.com/Monstercat'))

        # shouldn't match
        self.assertFalse(Mixer.can_handle_url('https://mixer.com'))
