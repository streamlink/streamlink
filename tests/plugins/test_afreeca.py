import unittest

from streamlink.plugins.afreeca import AfreecaTV


class TestPluginAfreecaTV(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "http://afreecatv.com/exampleuser",
            "http://afreecatv.com/exampleuser/123123123",
            "http://play.afreecatv.com/exampleuser",
            "http://play.afreecatv.com/exampleuser/123123123",
        ]
        for url in should_match:
            self.assertTrue(AfreecaTV.can_handle_url(url))

        should_not_match = [
            "http://www.afreecatv.com.tw",
            "http://www.afreecatv.jp",
        ]
        for url in should_not_match:
            self.assertFalse(AfreecaTV.can_handle_url(url))
