import unittest

from streamlink.plugins.powerapp import PowerApp


class TestPluginPowerApp(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://powerapp.com.tr/tv/powertv4k',
            'http://powerapp.com.tr/tv/powerturktv4k',
            'http://powerapp.com.tr/tv/powerEarthTV',
            'http://www.powerapp.com.tr/tvs/powertv'
        ]
        for url in should_match:
            self.assertTrue(PowerApp.can_handle_url(url), url)

    def test_can_handle_url_negative(self):
        should_not_match = [
            'http://powerapp.com.tr/',
        ]
        for url in should_not_match:
            self.assertFalse(PowerApp.can_handle_url(url))
