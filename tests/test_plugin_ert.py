import unittest

from streamlink.plugins.ert import Ert


class TestPluginErt(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://webtv.ert.gr/ert1/',
            'http://webtv.ert.gr/ert2/',
            'http://webtv.ert.gr/ert3/',
            'http://webtv.ert.gr/ertworld-live/',
            'http://webtv.ert.gr/ert-play-live/',
            'http://webtv.ert.gr/ert-play-2-live/',
        ]
        for url in should_match:
            self.assertTrue(Ert.can_handle_url(url))

        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Ert.can_handle_url(url))