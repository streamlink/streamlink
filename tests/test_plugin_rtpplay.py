import unittest

from streamlink.plugins.eurocom import Eurocom


class TestPluginEurocom(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Eurocom.can_handle_url("http://www.rtp.pt/play/"))
        self.assertTrue(Eurocom.can_handle_url("https://www.rtp.pt/play/"))

        # shouldn't match
        self.assertFalse(Eurocom.can_handle_url("https://www.rtp.pt/programa/"))
        self.assertFalse(Eurocom.can_handle_url("http://www.rtp.pt/programa/"))
        self.assertFalse(Eurocom.can_handle_url("https://media.rtp.pt/"))
        self.assertFalse(Eurocom.can_handle_url("http://media.rtp.pt/"))
