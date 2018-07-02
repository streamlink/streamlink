import unittest

from streamlink.plugins.pixiv import Pixiv


class TestPluginPixiv(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://sketch.pixiv.net/@exampleuser',
            'https://sketch.pixiv.net/@exampleuser/lives/000000000000000000',
        ]
        for url in should_match:
            self.assertTrue(Pixiv.can_handle_url(url))

        should_not_match = [
            'https://sketch.pixiv.net',
        ]
        for url in should_not_match:
            self.assertFalse(Pixiv.can_handle_url(url))
