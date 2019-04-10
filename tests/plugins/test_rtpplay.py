import unittest

from streamlink.plugins.rtpplay import RTPPlay


class TestPluginRTPPlay(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://www.rtp.pt/play/',
            'https://www.rtp.pt/play/',
            'https://www.rtp.pt/play/direto/rtp1',
            'https://www.rtp.pt/play/direto/rtpmadeira',
        ]
        for url in should_match:
            self.assertTrue(RTPPlay.can_handle_url(url), url)

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://www.rtp.pt/programa/',
            'http://www.rtp.pt/programa/',
            'https://media.rtp.pt/',
            'http://media.rtp.pt/',
        ]
        for url in should_not_match:
            self.assertFalse(RTPPlay.can_handle_url(url), url)
