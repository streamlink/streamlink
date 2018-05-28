import unittest

from streamlink.plugins.tigerdile import Tigerdile


class TestPluginTigerdile(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Tigerdile.can_handle_url("https://www.tigerdile.com/stream/example_streamer"))
        self.assertTrue(Tigerdile.can_handle_url("http://www.tigerdile.com/stream/example_streamer"))
        self.assertTrue(Tigerdile.can_handle_url("https://www.tigerdile.com/stream/example_streamer/"))
        self.assertTrue(Tigerdile.can_handle_url("http://www.tigerdile.com/stream/example_streamer/"))
        self.assertTrue(Tigerdile.can_handle_url("https://sfw.tigerdile.com/stream/example_streamer"))
        self.assertTrue(Tigerdile.can_handle_url("http://sfw.tigerdile.com/stream/example_streamer"))
        self.assertTrue(Tigerdile.can_handle_url("https://sfw.tigerdile.com/stream/example_streamer/"))
        self.assertTrue(Tigerdile.can_handle_url("http://sfw.tigerdile.com/stream/example_streamer/"))

        # shouldn't match
        self.assertFalse(Tigerdile.can_handle_url("http://www.tigerdile.com/"))
        self.assertFalse(Tigerdile.can_handle_url("http://www.tigerdile.com/stream"))
        self.assertFalse(Tigerdile.can_handle_url("http://www.tigerdile.com/stream/"))
        self.assertFalse(Tigerdile.can_handle_url("http://www.youtube.com/"))
