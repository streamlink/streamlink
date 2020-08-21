import unittest

from streamlink.plugins.nbcnews import Nbcnews


class TestPluginNBCNews(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.nbcnews.com/now/',
            'http://www.nbcnews.com/now/'
        ]
        for url in should_match:
            self.assertTrue(Nbcnews.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://www.nbcnews.com/',
            'http://www.nbcnews.com/'
        ]
        for url in should_not_match:
            self.assertFalse(Nbcnews.can_handle_url(url))
