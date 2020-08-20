import unittest

from streamlink.plugins.abcnews_go import AbcnewsGo


class TestPluginNbcnews(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(AbcnewsGo.can_handle_url("https://abcnews.go.com/live"))
        self.assertTrue(AbcnewsGo.can_handle_url("abcnews.go.com/live"))

        # shouldn't match
        self.assertFalse(AbcnewsGo.can_handle_url("http://www.youtube.com/"))