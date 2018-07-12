import unittest

from streamlink.plugins.liveme import LiveMe


class TestPluginLiveMe(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(LiveMe.can_handle_url('http://www.liveme.com/live.html?videoid=12312312312312312312'))
        self.assertTrue(LiveMe.can_handle_url('http://www.liveme.com/live.html?videoid=23123123123123123123&countryCode=undefined'))

        # shouldn't match
        self.assertFalse(LiveMe.can_handle_url('http://www.liveme.com/'))
        self.assertFalse(LiveMe.can_handle_url('http://www.liveme.com/explore.html'))
        self.assertFalse(LiveMe.can_handle_url('http://www.liveme.com/media/play'))
