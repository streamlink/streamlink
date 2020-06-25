import unittest

from streamlink.plugins.n13tv import N13TV


class TestPluginN13TV(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "http://13tv.co.il/live",
            "https://13tv.co.il/live",
            "http://www.13tv.co.il/live/",
            "https://www.13tv.co.il/live/",
            "http://13tv.co.il/item/entertainment/ambush/season-02/episodes/ffuk3-2026112/",
            "https://13tv.co.il/item/entertainment/ambush/season-02/episodes/ffuk3-2026112/",
            "http://www.13tv.co.il/item/entertainment/ambush/season-02/episodes/ffuk3-2026112/",
            "https://www.13tv.co.il/item/entertainment/ambush/season-02/episodes/ffuk3-2026112/"
            "http://13tv.co.il/item/entertainment/tzhok-mehamatzav/season-01/episodes/vkdoc-2023442/",
            "https://13tv.co.il/item/entertainment/tzhok-mehamatzav/season-01/episodes/vkdoc-2023442/",
            "http://www.13tv.co.il/item/entertainment/tzhok-mehamatzav/season-01/episodes/vkdoc-2023442/"
            "https://www.13tv.co.il/item/entertainment/tzhok-mehamatzav/season-01/episodes/vkdoc-2023442/"
        ]
        for url in should_match:
            self.assertTrue(N13TV.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            "https://www.youtube.com",
        ]
        for url in should_not_match:
            self.assertFalse(N13TV.can_handle_url(url))
