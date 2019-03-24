import unittest

from streamlink.plugins.okru import OKru


class TestPluginOKru(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://ok.ru/live/12345',
            'http://ok.ru/live/12345',
            'http://www.ok.ru/live/12345',
            'https://ok.ru/video/266205792931',
        ]
        for url in should_match:
            self.assertTrue(OKru.can_handle_url(url), url)

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://www.example.com',
        ]
        for url in should_not_match:
            self.assertFalse(OKru.can_handle_url(url), url)
