import unittest

from streamlink.plugins.gardenersworld import GardenersWorld


class TestPluginGardenersWorld(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://www.gardenersworld.com/',
        ]
        for url in should_match:
            self.assertTrue(GardenersWorld.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(GardenersWorld.can_handle_url(url))
