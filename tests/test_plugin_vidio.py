import unittest

from streamlink.plugins.vidio import Vidio


class TestPluginVidio(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Vidio.can_handle_url('https://www.vidio.com/live/204-sctv-tv-stream'))
        self.assertTrue(Vidio.can_handle_url('https://www.vidio.com/live/5075-dw-tv-stream'))
        self.assertTrue(Vidio.can_handle_url('https://www.vidio.com/watch/766861-5-rekor-fantastis-zidane-bersama-real-madrid'))

        # shouldn't match
        self.assertFalse(Vidio.can_handle_url('http://www.vidio.com'))
        self.assertFalse(Vidio.can_handle_url('https://www.vidio.com'))
