import unittest

from streamlink.plugins.ovvatv import OnePlusOne


class TestPluginOnePlusOne(unittest.TestCase):

    ''' Broken Plugin
    def test_can_handle_url(self):
        should_match = [
            '',
            '',
            '',
            '',
        ]
        for url in should_match:
            self.assertTrue(OnePlusOne.can_handle_url(url))
    '''

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com',
        ]
        for url in should_not_match:
            self.assertFalse(OnePlusOne.can_handle_url(url))
