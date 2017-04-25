import unittest

from streamlink.plugins.cyro import Cyro


class TestPluginCyro(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Cyro.can_handle_url("http://cyro.se/watch/foobar"))
        self.assertTrue(Cyro.can_handle_url("http://cyro.se/watch/foobar/s1/e4"))
        self.assertTrue(Cyro.can_handle_url("https://cyro.se/watch/barfoo"))
        self.assertTrue(Cyro.can_handle_url("https://cyro.se/watch/foobar/s1/e4"))

        # shouldn't match
        self.assertFalse(Cyro.can_handle_url("http://cyro.se"))
        self.assertFalse(Cyro.can_handle_url("https://cyro.se"))
