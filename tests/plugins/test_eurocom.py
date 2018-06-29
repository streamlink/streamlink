import unittest

from streamlink.plugins.eurocom import Eurocom


class TestPluginEurocom(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Eurocom.can_handle_url("http://eurocom.bg/live"))
        self.assertTrue(Eurocom.can_handle_url("http://eurocom.bg/live/"))
        self.assertTrue(Eurocom.can_handle_url("http://www.eurocom.bg/live/"))
        self.assertTrue(Eurocom.can_handle_url("http://www.eurocom.bg/live"))

        # shouldn't match
        self.assertFalse(Eurocom.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(Eurocom.can_handle_url("http://www.youtube.com/"))
