import unittest

from streamlink.plugins.ellobo import ElLobo


class TestPluginElLobo(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://www.ellobo106.com/index.php/vivo/solo-3audio',
        ]
        for url in should_match:
            self.assertTrue(ElLobo.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(ElLobo.can_handle_url(url))
