import unittest

from streamlink.plugins.youtube import YouTube, _url_re


class TestPluginYouTube(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "https://www.youtube.com/c/EXAMPLE/live",
            "https://www.youtube.com/c/EXAMPLE/live/",
            "https://www.youtube.com/channel/EXAMPLE",
            "https://www.youtube.com/v/aqz-KE-bpKQ",
            "https://www.youtube.com/embed/aqz-KE-bpKQ",
            "https://www.youtube.com/user/EXAMPLE/",
            "https://www.youtube.com/watch?v=aqz-KE-bpKQ",
            "https://www.youtube.com/embed/live_stream?channel=UCNye-wNBqNL5ZzHSJj3l8Bg",
        ]
        for url in should_match:
            self.assertTrue(YouTube.can_handle_url(url))

        should_not_match = [
            "https://www.youtube.com",
        ]
        for url in should_not_match:
            self.assertFalse(YouTube.can_handle_url(url))

    def _test_regex(self, url, expected_string, expected_group):
        m = _url_re.match(url)
        self.assertIsNotNone(m)
        self.assertEqual(expected_string, m.group(expected_group))

    def test_regex_liveChannel_c(self):
        self._test_regex("https://www.youtube.com/c/EXAMPLE/live",
                         "EXAMPLE", "liveChannel")

    def test_regex_liveChannel_no_c(self):
        self._test_regex("https://www.youtube.com/EXAMPLE1/live",
                         "EXAMPLE1", "liveChannel")

    def test_regex_user_channel(self):
        self._test_regex("https://www.youtube.com/channel/EXAMPLE2",
                         "EXAMPLE2", "user")

    def test_regex_user_user(self):
        self._test_regex("https://www.youtube.com/channel/EXAMPLE3",
                         "EXAMPLE3", "user")

    def test_regex_user_embed_list_stream(self):
        self._test_regex("https://www.youtube.com/embed/live_stream?channel=UCNye-wNBqNL5ZzHSJj3l8Bg",
                         "UCNye-wNBqNL5ZzHSJj3l8Bg", "user")

    def test_regex_user_embed_list_stream_2(self):
        self._test_regex("https://www.youtube.com/embed/live_stream?channel=UCNye-wNBqNL5ZzHSJj3l8Bg&autoplay=1&modestbranding=1&rel=0&showinfo=0&color=white&fs=1",
                         "UCNye-wNBqNL5ZzHSJj3l8Bg", "user")

    def test_regex_video_id_v(self):
        self._test_regex("https://www.youtube.com/v/aqz-KE-bpKQ",
                         "aqz-KE-bpKQ", "video_id")

    def test_regex_video_id_embed(self):
        self._test_regex("https://www.youtube.com/embed/aqz-KE-bpKQ",
                         "aqz-KE-bpKQ", "video_id")

    def test_regex_video_id_watch(self):
        self._test_regex("https://www.youtube.com/watch?v=aqz-KE-bpKQ",
                         "aqz-KE-bpKQ", "video_id")
