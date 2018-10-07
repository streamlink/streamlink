import unittest

from streamlink.plugins.ok_live import OK_live


class TestPluginOK_live(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(OK_live.can_handle_url("https://ok.ru/live/12345"))
        self.assertTrue(OK_live.can_handle_url("http://ok.ru/live/12345"))
        self.assertTrue(OK_live.can_handle_url("http://www.ok.ru/live/12345"))
        self.assertTrue(OK_live.can_handle_url("https://ok.ru/video/266205792931"))

        # shouldn't match
        self.assertFalse(OK_live.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(OK_live.can_handle_url("http://www.youtube.com/"))
