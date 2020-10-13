import unittest

from streamlink.plugins.bigo import Bigo


class TestPluginBigo(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "http://bigo.tv/00000000",
            "https://bigo.tv/00000000",
            "https://www.bigo.tv/00000000",
            "http://www.bigo.tv/00000000",
            "http://www.bigo.tv/fancy1234",
            "http://www.bigo.tv/abc.123",
            "http://www.bigo.tv/000000.00"
        ]
        for url in should_match:
            self.assertTrue(Bigo.can_handle_url(url), url)

    def test_can_handle_url_negative(self):
        should_not_match = [
            # Old URLs don't work anymore
            "http://live.bigo.tv/00000000",
            "https://live.bigo.tv/00000000",
            "http://www.bigoweb.co/show/00000000",
            "https://www.bigoweb.co/show/00000000",
            "http://bigoweb.co/show/00000000",
            "https://bigoweb.co/show/00000000"

            # Wrong URL structure
            "https://www.bigo.tv/show/00000000",
            "http://www.bigo.tv/show/00000000",
            "http://bigo.tv/show/00000000",
            "https://bigo.tv/show/00000000"
        ]
        for url in should_not_match:
            self.assertFalse(Bigo.can_handle_url(url), url)
