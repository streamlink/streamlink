import unittest

from streamlink.plugins.youtube import YouTube


class TestPluginYouTube(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "https://www.youtube.com/c/EXAMPLE/live",
            "https://www.youtube.com/channel/EXAMPLE",
            "https://www.youtube.com/v/aqz-KE-bpKQ",
            "https://www.youtube.com/embed/aqz-KE-bpKQ",
            "https://www.youtube.com/user/EXAMPLE/",
            "https://www.youtube.com/watch?v=aqz-KE-bpKQ",
        ]
        for url in should_match:
            self.assertTrue(YouTube.can_handle_url(url))

        should_not_match = [
            "https://www.youtube.com",
        ]
        for url in should_not_match:
            self.assertFalse(YouTube.can_handle_url(url))
