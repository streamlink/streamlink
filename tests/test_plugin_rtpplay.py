import unittest

from streamlink.plugins.rtpplay import RTPPlay


class TestPluginRTPPlay(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(RTPPlay.can_handle_url("http://www.rtp.pt/play/"))
        self.assertTrue(RTPPlay.can_handle_url("https://www.rtp.pt/play/"))

        # shouldn't match
        self.assertFalse(RTPPlay.can_handle_url("https://www.rtp.pt/programa/"))
        self.assertFalse(RTPPlay.can_handle_url("http://www.rtp.pt/programa/"))
        self.assertFalse(RTPPlay.can_handle_url("https://media.rtp.pt/"))
        self.assertFalse(RTPPlay.can_handle_url("http://media.rtp.pt/"))
