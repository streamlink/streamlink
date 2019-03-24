import unittest

from streamlink.plugins.facebook import Facebook


class TestPluginFacebook(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Facebook.can_handle_url("https://www.facebook.com/nos/videos/1725546430794241/"))
        self.assertTrue(Facebook.can_handle_url("https://www.facebook.com/nytfood/videos/1485091228202006/"))
        self.assertTrue(Facebook.can_handle_url("https://www.facebook.com/SporTurkTR/videos/798553173631138/"))
        self.assertTrue(Facebook.can_handle_url("https://www.facebook.com/119555411802156/posts/500665313691162/"))
        self.assertTrue(Facebook.can_handle_url("https://www.facebookcorewwwi.onion/SporTurkTR/videos/798553173631138/"))

        # shouldn't match
        self.assertFalse(Facebook.can_handle_url("https://www.facebook.com"))
