import unittest

from streamlink.plugins.webtv import WebTV


class TestPluginWebTV(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(WebTV.can_handle_url("http://planetmutfak.web.tv"))
        self.assertTrue(WebTV.can_handle_url("http://telex.web.tv"))
        self.assertTrue(WebTV.can_handle_url("http://nasamedia.web.tv"))
        self.assertTrue(WebTV.can_handle_url("http://genctv.web.tv"))
        self.assertTrue(WebTV.can_handle_url("http://etvmanisa.web.tv"))
        self.assertTrue(WebTV.can_handle_url("http://startv.web.tv"))
        self.assertTrue(WebTV.can_handle_url("http://akuntv.web.tv"))
        self.assertTrue(WebTV.can_handle_url("http://telebarnn.web.tv"))
        self.assertTrue(WebTV.can_handle_url("http://kanal48.web.tv"))
        self.assertTrue(WebTV.can_handle_url("http://digi24tv.web.tv"))
        self.assertTrue(WebTV.can_handle_url("http://french24.web.tv"))

        # shouldn't match
        self.assertFalse(WebTV.can_handle_url("http://www.youtube.com/"))
        self.assertFalse(WebTV.can_handle_url("https://www.tvplayer.com/watch/itv"))
        self.assertFalse(WebTV.can_handle_url("https://tvplayer.com/watch/itv"))
