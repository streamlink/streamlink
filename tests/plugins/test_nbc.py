import unittest

from streamlink.plugins.nbc import NBC


class TestPluginNBC(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.nbc.com/nightly-news/video/nbc-nightly-news-jun-29-2018/3745314',
        ]
        for url in should_match:
            self.assertTrue(NBC.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(NBC.can_handle_url(url))
