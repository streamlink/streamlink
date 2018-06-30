import unittest

from streamlink.plugins.trtspor import TRTSpor


class TestPluginTRTSpor(unittest.TestCase):

    ''' Plugin URL Broken
    def test_can_handle_url(self):
        should_match = [
            'http://www.trtspor.com.tr/canli-yayin-izle/trt-spor-159/',
        ]
        for url in should_match:
            self.assertTrue(TRTSpor.can_handle_url(url))
    '''

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(TRTSpor.can_handle_url(url))
