import unittest

from streamlink.plugins.mitele import Mitele


class TestPluginMitele(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "http://www.mitele.es/directo/bemad",
            "http://www.mitele.es/directo/boing",
            "http://www.mitele.es/directo/cuatro",
            "http://www.mitele.es/directo/divinity",
            "http://www.mitele.es/directo/energy",
            "http://www.mitele.es/directo/fdf",
            "http://www.mitele.es/directo/telecinco",
            "https://www.mitele.es/directo/gh-duo-24h-senal-1",
            "https://www.mitele.es/directo/gh-duo-24h-senal-2",
        ]
        for url in should_match:
            self.assertTrue(Mitele.can_handle_url(url))

        should_not_match = [
            "http://www.mitele.es",
        ]
        for url in should_not_match:
            self.assertFalse(Mitele.can_handle_url(url))
