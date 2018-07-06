import unittest

from streamlink.plugins.dogan import Dogan


class TestPluginDogan(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.cnnturk.com/canli-yayin',
            'https://www.dreamturk.com.tr/canli',
            'https://www.dreamtv.com.tr/canli-yayin',
            'https://www.kanald.com.tr/canli-yayin',
            'https://www.teve2.com.tr/canli-yayin',
        ]
        for url in should_match:
            self.assertTrue(Dogan.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Dogan.can_handle_url(url))
