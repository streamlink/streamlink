import unittest

from streamlink.plugins.canalsur import CanalSur


class TestPluginCanalSur(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://www.canalsur.es/tv_directo-1193.html',
        ]
        for url in should_match:
            self.assertTrue(CanalSur.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(CanalSur.can_handle_url(url))
