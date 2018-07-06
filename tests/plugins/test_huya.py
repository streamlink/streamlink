import unittest

from streamlink.plugins.huya import Huya


class TestPluginHuya(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://www.huya.com/123123123',
            'http://www.huya.com/name',
            'https://www.huya.com/123123123',
        ]
        for url in should_match:
            self.assertTrue(Huya.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'http://www.huya.com',
        ]
        for url in should_not_match:
            self.assertFalse(Huya.can_handle_url(url))
