import unittest

from streamlink.plugins.earthcam import EarthCam


class TestPluginEarthCam(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.earthcam.com/usa/newyork/timessquare/?cam=tsstreet',
            'https://www.earthcam.com/usa/newyork/timessquare/?cam=gts1',
        ]
        for url in should_match:
            self.assertTrue(EarthCam.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(EarthCam.can_handle_url(url))
