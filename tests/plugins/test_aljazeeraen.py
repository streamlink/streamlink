import unittest

from streamlink.plugins.aljazeeraen import AlJazeeraEnglish


class TestPluginAlJazeeraEnglish(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.aljazeera.com/live/',
            'https://www.aljazeera.com/programmes/techknow/2017/04/science-sugar-170429141233635.html',
        ]
        for url in should_match:
            self.assertTrue(AlJazeeraEnglish.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(AlJazeeraEnglish.can_handle_url(url))
