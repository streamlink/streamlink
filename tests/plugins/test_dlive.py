import unittest

from streamlink.plugins.dlive import dlive


class TestPluginDlive(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(dlive.can_handle_url("https://dlive.tv/pewdiepie"))
