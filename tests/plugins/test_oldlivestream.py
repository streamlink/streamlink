import unittest

from streamlink.plugins.oldlivestream import OldLivestream


class TestPluginOldLivestream(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(OldLivestream.can_handle_url("https://cdn.livestream.com/embed/channel"))
        self.assertTrue(OldLivestream.can_handle_url("https://original.livestream.com/embed/channel"))
        self.assertTrue(OldLivestream.can_handle_url("https://original.livestream.com/channel"))

        # shouldn't match
        self.assertFalse(OldLivestream.can_handle_url("https://cdn.livestream.com"))
        self.assertFalse(OldLivestream.can_handle_url("https://original.livestream.com"))
        # other plugin livestream.py
        self.assertFalse(OldLivestream.can_handle_url("https://livestream.com"))
        self.assertFalse(OldLivestream.can_handle_url("https://www.livestream.com"))
