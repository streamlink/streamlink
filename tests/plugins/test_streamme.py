import unittest

from streamlink.plugins.streamme import StreamMe


class TestPluginStreamMe(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(StreamMe.can_handle_url("http://www.stream.me/nameofstream"))
        self.assertTrue(StreamMe.can_handle_url("https://stream.me/nameofstream"))

        # shouldn't match
        self.assertFalse(StreamMe.can_handle_url("http://www.livestream.me/nameofstream"))
        self.assertFalse(StreamMe.can_handle_url("http://www.streamme.com/nameofstream"))
        self.assertFalse(StreamMe.can_handle_url("http://www.streamme.me/nameofstream"))
        self.assertFalse(StreamMe.can_handle_url("http://www.youtube.com/"))
