import unittest

from streamlink.plugins.reuters import Reuters


class TestPluginReuters(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.reuters.tv/l/PFJx/2019/04/19/way-of-the-cross-ritual-around-notre-dame-cathedral',
            'https://www.reuters.tv/l/PFcO/2019/04/10/first-ever-black-hole-image-released-astrophysics-milestone',
            'https://www.reuters.tv/p/WoRwM1a00y8',
        ]
        for url in should_match:
            self.assertTrue(Reuters.can_handle_url(url), url)

        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Reuters.can_handle_url(url), url)
