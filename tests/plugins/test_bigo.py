import unittest

from streamlink.plugins.bigo import Bigo


class TestPluginBigo(unittest.TestCase):
    def test_can_handle_url(self):
        # Correct urls
        self.assertTrue(Bigo.can_handle_url("http://bigo.tv/00000000"))
        self.assertTrue(Bigo.can_handle_url("https://bigo.tv/00000000"))
        self.assertTrue(Bigo.can_handle_url("https://www.bigo.tv/00000000"))
        self.assertTrue(Bigo.can_handle_url("http://www.bigo.tv/00000000"))
        self.assertTrue(Bigo.can_handle_url("http://www.bigo.tv/fancy1234"))
        self.assertTrue(Bigo.can_handle_url("http://www.bigo.tv/abc.123"))
        self.assertTrue(Bigo.can_handle_url("http://www.bigo.tv/000000.00"))

        # Old URLs don't work anymore
        self.assertFalse(Bigo.can_handle_url("http://live.bigo.tv/00000000"))
        self.assertFalse(Bigo.can_handle_url("https://live.bigo.tv/00000000"))
        self.assertFalse(Bigo.can_handle_url("http://www.bigoweb.co/show/00000000"))
        self.assertFalse(Bigo.can_handle_url("https://www.bigoweb.co/show/00000000"))
        self.assertFalse(Bigo.can_handle_url("http://bigoweb.co/show/00000000"))
        self.assertFalse(Bigo.can_handle_url("https://bigoweb.co/show/00000000"))

        # Wrong URL structure
        self.assertFalse(Bigo.can_handle_url("ftp://www.bigo.tv/00000000"))
        self.assertFalse(Bigo.can_handle_url("https://www.bigo.tv/show/00000000"))
        self.assertFalse(Bigo.can_handle_url("http://www.bigo.tv/show/00000000"))
        self.assertFalse(Bigo.can_handle_url("http://bigo.tv/show/00000000"))
        self.assertFalse(Bigo.can_handle_url("https://bigo.tv/show/00000000"))
