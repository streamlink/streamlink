import unittest

from streamlink.plugins.channel_one import Channel_One


class TestPluginChannel_One(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.1tv.ru/live/',
            'http://www.1tv.ru/live/'
        ]
        for url in should_match:
            self.assertTrue(Channel_One.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://www.1tv.ru/',
            'http://www.1tv.ru/'
        ]
        for url in should_not_match:
            self.assertFalse(Channel_One.can_handle_url(url))
