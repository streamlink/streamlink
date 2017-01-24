import unittest

from streamlink.plugins.swisstxt import Swisstxt


class TestPluginSwisstxt(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Swisstxt.can_handle_url("http://www.srf.ch/sport/resultcenter/tennis?eventId=338052"))
        self.assertTrue(Swisstxt.can_handle_url("http://live.rsi.ch/tennis.html?eventId=338052"))
        self.assertTrue(Swisstxt.can_handle_url("http://live.rsi.ch/sport.html?eventId=12345"))

        # shouldn't match
        # regular srgssr sites
        self.assertFalse(Swisstxt.can_handle_url("http://srf.ch/play/tv/live"))
        self.assertFalse(Swisstxt.can_handle_url("http://www.rsi.ch/play/tv/live#?tvLiveId=livestream_La1"))
        self.assertFalse(Swisstxt.can_handle_url("http://rsi.ch/play/tv/live?tvLiveId=livestream_La1"))
        self.assertFalse(Swisstxt.can_handle_url("http://www.rtr.ch/play/tv/live"))
        self.assertFalse(Swisstxt.can_handle_url("http://rtr.ch/play/tv/live"))
        self.assertFalse(Swisstxt.can_handle_url("http://rts.ch/play/tv/direct#?tvLiveId=3608506"))
        self.assertFalse(Swisstxt.can_handle_url("http://www.srf.ch/play/tv/live#?tvLiveId=c49c1d64-9f60-0001-1c36-43c288c01a10"))
        self.assertFalse(Swisstxt.can_handle_url("http://www.rts.ch/sport/direct/8328501-tennis-open-daustralie.html"))
        self.assertFalse(Swisstxt.can_handle_url("http://www.rts.ch/play/tv/tennis/video/tennis-open-daustralie?id=8328501"))

        # other sites
        self.assertFalse(Swisstxt.can_handle_url("http://www.crunchyroll.com/gintama"))
        self.assertFalse(Swisstxt.can_handle_url("http://www.crunchyroll.es/gintama"))
        self.assertFalse(Swisstxt.can_handle_url("http://www.youtube.com/"))
