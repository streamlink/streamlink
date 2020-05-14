import unittest

from streamlink.plugins.youtube import YouTube, _url_re


class TestPluginYouTube(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "https://www.youtube.com/EXAMPLE/live",
            "https://www.youtube.com/c/EXAMPLE",
            "https://www.youtube.com/c/EXAMPLE/",
            "https://www.youtube.com/c/EXAMPLE/live",
            "https://www.youtube.com/c/EXAMPLE/live/",
            "https://www.youtube.com/channel/EXAMPLE",
            "https://www.youtube.com/channel/EXAMPLE/",
            "https://www.youtube.com/embed/aqz-KE-bpKQ",
            "https://www.youtube.com/embed/live_stream?channel=UCNye-wNBqNL5ZzHSJj3l8Bg",
            "https://www.youtube.com/user/EXAMPLE",
            "https://www.youtube.com/user/EXAMPLE/",
            "https://www.youtube.com/user/EXAMPLE/live",
            "https://www.youtube.com/v/aqz-KE-bpKQ",
            "https://www.youtube.com/watch?v=aqz-KE-bpKQ",
        ]
        for url in should_match:
            self.assertTrue(YouTube.can_handle_url(url), url)

        should_not_match = [
            "https://accounts.google.com/",
            "https://www.youtube.com",
            "https://www.youtube.com/account",
            "https://www.youtube.com/feed/guide_builder",
            "https://www.youtube.com/t/terms",
        ]
        for url in should_not_match:
            self.assertFalse(YouTube.can_handle_url(url), url)

    def _test_regex(self, url, expected_string, expected_group):
        m = _url_re.match(url)
        self.assertIsNotNone(m)
        self.assertEqual(expected_string, m.group(expected_group))

    def test_regex_video_id_v(self):
        self._test_regex("https://www.youtube.com/v/aqz-KE-bpKQ",
                         "aqz-KE-bpKQ", "video_id")

    def test_regex_video_id_embed(self):
        self._test_regex("https://www.youtube.com/embed/aqz-KE-bpKQ",
                         "aqz-KE-bpKQ", "video_id")

    def test_regex_video_id_watch(self):
        self._test_regex("https://www.youtube.com/watch?v=aqz-KE-bpKQ",
                         "aqz-KE-bpKQ", "video_id")
