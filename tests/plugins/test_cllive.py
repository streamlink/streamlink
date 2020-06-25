import unittest

from streamlink.plugins.cllive import CLLive


class TestPluginBigo(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "https://www.cl-live.com/programs/ondemand/uaTj4ds5VuZVsCMva7C7Hv",
            "https://www.cl-live.com/programs/ondemand/hVVBrv6ffY7H5cVZSF9eK2"
        ]
        for url in should_match:
            self.assertTrue(CLLive.can_handle_url(url), url)

    def test_can_handle_url_negative(self):
        should_not_match = [
            # Wrong URL structure
            "https://www.cl-live.com/programs/cast/3Sb3i75Y1KDDRhriMxoTsW"
        ]
        for url in should_not_match:
            self.assertFalse(CLLive.can_handle_url(url), url)
