import unittest

from streamlink.plugins.mrtmk import MRTmk


class TestPluginMRTmk(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://play.mrt.com.mk/live/658323455489957',
            'http://play.mrt.com.mk/live/47',
            'http://play.mrt.com.mk/play/1581',
        ]
        for url in should_match:
            self.assertTrue(MRTmk.can_handle_url(url), url)

    def test_can_handle_url_negative(self):
        should_not_match = [
            'http://play.mrt.com.mk/',
            'http://play.mrt.com.mk/c/2',
        ]
        for url in should_not_match:
            self.assertFalse(MRTmk.can_handle_url(url), url)
