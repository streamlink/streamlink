import unittest

from streamlink.plugins.startv import StarTV


class TestPluginStarTV(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.startv.com.tr/canli-yayin',
        ]
        for url in should_match:
            self.assertTrue(StarTV.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(StarTV.can_handle_url(url))
