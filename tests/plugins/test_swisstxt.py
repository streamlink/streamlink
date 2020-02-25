import unittest

from streamlink.plugins.swisstxt import Swisstxt


class TestPluginSwisstxt(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "http://www.srf.ch/sport/resultcenter/tennis?eventId=338052",
            "http://live.rsi.ch/tennis.html?eventId=338052",
            "http://live.rsi.ch/sport.html?eventId=12345"
        ]
        for url in should_match:
            self.assertTrue(Swisstxt.can_handle_url(url))

        should_not_match = [
            # regular srgssr sites
            "http://srf.ch/play/tv/live",
            "http://www.rsi.ch/play/tv/live#?tvLiveId=livestream_La1",
            "http://rsi.ch/play/tv/live?tvLiveId=livestream_La1",
            "http://www.rtr.ch/play/tv/live",
            "http://rtr.ch/play/tv/live",
            "http://rts.ch/play/tv/direct#?tvLiveId=3608506",
            "http://www.srf.ch/play/tv/live#?tvLiveId=c49c1d64-9f60-0001-1c36-43c288c01a10",
            "http://www.rts.ch/sport/direct/8328501-tennis-open-daustralie.html",
            "http://www.rts.ch/play/tv/tennis/video/tennis-open-daustralie?id=8328501",
            # other sites
            "http://www.crunchyroll.com/gintama",
            "http://www.crunchyroll.es/gintama",
            "http://www.youtube.com/"
        ]
        for url in should_not_match:
            self.assertFalse(Swisstxt.can_handle_url(url))
