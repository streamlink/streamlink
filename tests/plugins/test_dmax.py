import unittest

from streamlink.plugins.reuters import Reuters


class TestPluginDmax(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.dmax.de/programme/border-control/video/episode-21/DCB466460001100',
            'https://www.dmax.de/programme/mythbusters/video/die-ruckkehr-des-klebebands/DCB395260001100',
            'https://www.dmax.de/programme/a2/video/episode-22/DCB472860002100',
        ]
        for url in should_match:
            self.assertTrue(Reuters.can_handle_url(url), url)

        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Reuters.can_handle_url(url), url)