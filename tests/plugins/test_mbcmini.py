import unittest

from streamlink.plugins.mbcmini import Mbcmini


class TestPluginMbcmini(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://miniplay.imbc.com/WebLiveURL.ashx?channel=sfm',
            'http://miniplay.imbc.com/WebLiveURL.ashx?channel=mfm',
            'http://miniplay.imbc.com/WebLiveURL.ashx?channel=chm',
            'https://miniplay.imbc.com/WebLiveURL.ashx?channel=sfm',
            'https://miniplay.imbc.com/WebLiveURL.ashx?channel=mfm',
            'https://miniplay.imbc.com/WebLiveURL.ashx?channel=chm',
        ]
        for url in should_match:
            self.assertTrue(Mbcmini.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Mbcmini.can_handle_url(url))
