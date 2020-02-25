import unittest

from streamlink.plugins.cnews import CNEWS


class TestPluginCNEWS(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "http://www.cnews.fr/le-direct",
            "http://www.cnews.fr/direct",
            "http://www.cnews.fr/emission/2018-06-12/meteo-du-12062018-784730",
            "http://www.cnews.fr/emission/2018-06-12/le-journal-des-faits-divers-du-12062018-784704"
        ]
        for url in should_match:
            self.assertTrue(CNEWS.can_handle_url(url))

        should_not_match = [
            "http://www.cnews.fr/",
            "http://www.tvcatchup.com/",
            "http://www.youtube.com/"
        ]
        for url in should_not_match:
            self.assertFalse(CNEWS.can_handle_url(url))
