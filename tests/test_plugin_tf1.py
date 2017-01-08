import unittest

from streamlink.plugins.tf1 import TF1


class TestPluginTF1(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(TF1.can_handle_url("http://tf1.fr/tf1/direct/"))
        self.assertTrue(TF1.can_handle_url("http://lci.fr/direct"))
        self.assertTrue(TF1.can_handle_url("http://www.lci.fr/direct"))
        self.assertTrue(TF1.can_handle_url("http://tf1.fr/tmc/direct"))

        # shouldn't match
        self.assertFalse(TF1.can_handle_url("http://tf1.fr/direct"))
        self.assertFalse(TF1.can_handle_url("http://www.tf1.fr/direct"))
        self.assertFalse(TF1.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(TF1.can_handle_url("http://www.youtube.com/"))
