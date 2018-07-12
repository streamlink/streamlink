import unittest

from streamlink.plugins.cinergroup import CinerGroup


class TestPluginCinerGroup(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://showtv.com.tr/canli-yayin',
            'http://haberturk.com/canliyayin',
            'http://showmax.com.tr/canliyayin',
            'http://showturk.com.tr/canli-yayin/showturk',
            'http://bloomberght.com/tv',
            'http://haberturk.tv/canliyayin',
        ]
        for url in should_match:
            self.assertTrue(CinerGroup.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(CinerGroup.can_handle_url(url))
