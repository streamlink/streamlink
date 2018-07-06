import unittest

from streamlink.plugins.tga import Tga


class TestPluginTga(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://star.longzhu.com/lpl',
            'http://y.longzhu.com/y123123?from=tonglan2.1',
            'http://star.longzhu.com/123123?from=tonglan4.3',
        ]
        for url in should_match:
            self.assertTrue(Tga.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Tga.can_handle_url(url))
