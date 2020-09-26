import unittest

from streamlink.plugins.cdnbg import CDNBG


class TestPluginCDNBG(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://bgonair.bg/tvonline',
            'http://bgonair.bg/tvonline/',
            'http://www.nova.bg/live',
            'http://nova.bg/live',
            'http://bnt.bg/live',
            'http://bnt.bg/live/bnt1',
            'http://bnt.bg/live/bnt2',
            'http://bnt.bg/live/bnt3',
            'http://bnt.bg/live/bnt4',
            'http://tv.bnt.bg/bnt1',
            'http://tv.bnt.bg/bnt2',
            'http://tv.bnt.bg/bnt3',
            'http://tv.bnt.bg/bnt4',
            'http://mu-vi.tv/LiveStreams/pages/Live.aspx',
            'http://live.bstv.bg/',
            'https://www.bloombergtv.bg/video',
            'https://i.cdn.bg/live/xfr3453g0d',
        ]
        for url in should_match:
            self.assertTrue(CDNBG.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'http://www.tvcatchup.com/',
            'http://www.youtube.com/',
            'https://www.tvevropa.com',
            'http://www.kanal3.bg/live',
            'http://inlife.bg/',
            'http://videochanel.bstv.bg',
            'http://video.bstv.bg/',
            'http://bitelevision.com/live',
            'http://mmtvmusic.com/live/',
            'http://chernomore.bg/',
        ]
        for url in should_not_match:
            self.assertFalse(CDNBG.can_handle_url(url))
