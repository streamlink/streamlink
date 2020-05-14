import unittest

from streamlink.plugins.zeenews import ZeeNews


class TestPluginZeeNews(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://zeenews.india.com/live-tv',
            'https://zeenews.india.com/live-tv/embed',
        ]
        for url in should_match:
            self.assertTrue(ZeeNews.can_handle_url(url), url)

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(ZeeNews.can_handle_url(url), url)
