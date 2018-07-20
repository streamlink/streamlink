import unittest

from streamlink.plugins.abematv import AbemaTV


class TestPluginAbemaTV(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://abema.tv/now-on-air/abema-news',
            'https://abema.tv/video/episode/90-1053_s99_p12',
            'https://abema.tv/channels/everybody-anime/slots/FJcUsdYjTk1rAb',
            'https://abema.tv/now-on-air/abema-news?a=b&c=d',
            'https://abema.tv/video/episode/90-1053_s99_p12?a=b&c=d',
            'https://abema.tv/channels/abema-anime/slots/9rTULtcJFiFmM9?a=b'
        ]
        for url in should_match:
            self.assertTrue(AbemaTV.can_handle_url(url))

        should_not_match = [
            'http://abema.tv/now-on-air/abema-news',
            'http://www.abema.tv/now-on-air/abema-news',
            'https://www.abema.tv/now-on-air/abema-news',
            'https://www.abema.tv/now-on-air/',
            'https://abema.tv/timetable',
            'https://abema.tv/video',
            'https://abema.tv/video/title/13-47',
            'https://abema.tv/video/title/13-47?a=b'
        ]
        for url in should_not_match:
            self.assertFalse(AbemaTV.can_handle_url(url))
