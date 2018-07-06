import unittest

from streamlink.plugins.ceskatelevize import Ceskatelevize


class TestPluginCeskatelevize(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://www.ceskatelevize.cz/ct1/zive/',
            'http://www.ceskatelevize.cz/ct2/zive/',
            'http://www.ceskatelevize.cz/ct24/',
            'http://www.ceskatelevize.cz/sport/zive-vysilani/',
            'http://decko.ceskatelevize.cz/zive/',
            'http://www.ceskatelevize.cz/art/zive/',
        ]
        for url in should_match:
            self.assertTrue(Ceskatelevize.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Ceskatelevize.can_handle_url(url))
