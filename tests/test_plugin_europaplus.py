import unittest

from streamlink.plugins.europaplus import EuropaPlusTV


class TestPluginEuronews(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(EuropaPlusTV.can_handle_url("http://www.europaplus.ru/europaplustv"))
        self.assertTrue(EuropaPlusTV.can_handle_url("http://europaplus.ru/europaplustv"))
        self.assertTrue(EuropaPlusTV.can_handle_url("https://europaplus.ru/europaplustv"))
        self.assertTrue(EuropaPlusTV.can_handle_url("https://www.europaplus.ru/europaplustv"))

        # shouldn't match
        self.assertFalse(EuropaPlusTV.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(EuropaPlusTV.can_handle_url("http://www.youtube.com/"))
