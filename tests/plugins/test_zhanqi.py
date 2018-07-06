import unittest

from streamlink.plugins.zhanqi import Zhanqitv


class TestPluginZhanqitv(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.zhanqi.tv/lpl',
        ]
        for url in should_match:
            self.assertTrue(Zhanqitv.can_handle_url(url))

        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Zhanqitv.can_handle_url(url))
