import unittest

from streamlink.plugins.tvtoya import TVToya


class TestPluginTVRPlus(unittest.TestCase):
    def test_can_handle_url(self):
        self.assertTrue(TVToya.can_handle_url("https://tvtoya.pl/live"))
        self.assertTrue(TVToya.can_handle_url("http://tvtoya.pl/live"))

    def test_can_handle_url_negative(self):
        self.assertFalse(TVToya.can_handle_url("https://tvtoya.pl"))
        self.assertFalse(TVToya.can_handle_url("http://tvtoya.pl"))
        self.assertFalse(TVToya.can_handle_url("http://tvtoya.pl/other-page"))
        self.assertFalse(TVToya.can_handle_url("http://tvtoya.pl/"))
        self.assertFalse(TVToya.can_handle_url("https://tvtoya.pl/"))
