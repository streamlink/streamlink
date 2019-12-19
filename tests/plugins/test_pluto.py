import unittest

from streamlink.plugins.pluto import Pluto


class TestPluginPluto(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Pluto.can_handle_url("https://pluto.tv/live-tv/asdf"))
        self.assertTrue(Pluto.can_handle_url("http://www.pluto.tv/live-tv/channel-lineup"))
        self.assertTrue(Pluto.can_handle_url("http://pluto.tv/live-tv/nfl-channel"))
        self.assertTrue(Pluto.can_handle_url("https://pluto.tv/live-tv/red-bull-tv-2/"))
        self.assertTrue(Pluto.can_handle_url("https://pluto.tv/live-tv/4k-tv/"))

        # shouldn't match
        self.assertFalse(Pluto.can_handle_url("https://fake.pluto.tv/live-tv/hello"))
        self.assertFalse(Pluto.can_handle_url("https://www.pluto.tv/live-tv/"))
        self.assertFalse(Pluto.can_handle_url("https://pluto.tv/live-tv//"))
        self.assertFalse(Pluto.can_handle_url("https://www.pluto.com/live-tv/swag/"))
        self.assertFalse(Pluto.can_handle_url("https://youtube.com/live-tv/swag.html"))


if __name__ == "__main__":
    unittest.main()
