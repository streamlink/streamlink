import unittest

from streamlink.plugins.chaturbate import Chaturbate


class TestPluginChaturbate(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Chaturbate.can_handle_url("https://chaturbate.com/username"))
        self.assertTrue(Chaturbate.can_handle_url("https://m.chaturbate.com/username"))
        self.assertTrue(Chaturbate.can_handle_url("https://www.chaturbate.com/username"))

        # shouldn't match
        self.assertFalse(Chaturbate.can_handle_url("http://local.local/"))
        self.assertFalse(Chaturbate.can_handle_url("http://localhost.localhost/"))
