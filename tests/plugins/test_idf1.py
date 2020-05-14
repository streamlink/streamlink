import unittest

from streamlink.plugins.idf1 import IDF1


class TestPluginIDF1(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(IDF1.can_handle_url("https://www.idf1.fr/live"))
        self.assertTrue(IDF1.can_handle_url("https://www.idf1.fr/videos/jlpp/best-of-2018-02-24-partie-2.html"))
        self.assertTrue(IDF1.can_handle_url("http://www.idf1.fr/videos/buzz-de-noel/partie-2.html"))

        # shouldn't match
        self.assertFalse(IDF1.can_handle_url("https://www.idf1.fr/"))
        self.assertFalse(IDF1.can_handle_url("https://www.idf1.fr/videos"))
        self.assertFalse(IDF1.can_handle_url("https://www.idf1.fr/programmes/emissions/idf1-chez-vous.html"))
        self.assertFalse(IDF1.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(IDF1.can_handle_url("http://www.youtube.com/"))
