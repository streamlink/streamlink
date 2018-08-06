import unittest

from streamlink.plugins.camsoda import Camsoda


class TestPluginCamsoda(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Camsoda.can_handle_url("https://www.camsoda.com/stream-name"))
        self.assertTrue(Camsoda.can_handle_url("https://www.camsoda.com/streamname"))
        self.assertTrue(Camsoda.can_handle_url("https://www.camsoda.com/username"))
        self.assertTrue(Camsoda.can_handle_url("https://www.camsoda.com/username/"))

    def test_can_handle_url_negative(self):
        # shouldn't match
        self.assertFalse(Camsoda.can_handle_url("https://www.camsoda.com/media/user/t/123"))
        self.assertFalse(Camsoda.can_handle_url("http://local.local/"))
        self.assertFalse(Camsoda.can_handle_url("http://localhost.localhost/"))
