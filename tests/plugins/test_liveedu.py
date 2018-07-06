import unittest

from streamlink.plugins.liveedu import LiveEdu


class TestPluginLiveEdu(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.liveedu.tv/',
        ]
        for url in should_match:
            self.assertTrue(LiveEdu.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(LiveEdu.can_handle_url(url))
