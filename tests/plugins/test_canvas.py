import unittest

from streamlink.plugins.canvas import Canvas


class TestPluginCanvas(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://canvas.instructure.com/media_objects/m-Zeo1NE689yHQMYUXzRX4yIEtoNOIymxP/',
        ]
        for url in should_match:
            self.assertTrue(Canvas.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Canvas.can_handle_url(url))
