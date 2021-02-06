import unittest

from streamlink.plugins.nasa import Nasa


class TestPluginNasa(unittest.TestCase):
    def test_can_handle_url_positive(self):
        should_match = [
            "https://www.nasa.gov/multimedia/nasatv/index.html#public",
            "https://www.nasa.gov/multimedia/nasatv/index.html#media",
            "https://www.nasa.gov/multimedia/nasatv/#public",
            "https://www.nasa.gov/multimedia/nasatv/#media",
        ]
        for url in should_match:
            self.assertTrue(Nasa.can_handle_url(url), url)

    def test_can_handle_url_negative(self):
        should_not_match = [
            "https://www.nasa.gov/multimedia/nasatv/index.html",
            "https://www.nasa.gov/multimedia/nasatv/index.html#",
            "https://www.nasa.gov/multimedia/nasatv/index.html#foo",
            "https://www.nasa.gov/multimedia/nasatv/",
            "https://www.nasa.gov/multimedia/nasatv/#",
            "https://www.nasa.gov/multimedia/nasatv/#foo",
        ]
        for url in should_not_match:
            self.assertFalse(Nasa.can_handle_url(url), url)
