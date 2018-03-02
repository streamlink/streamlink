import unittest

from streamlink.plugins.balticlivecam import BalticLivecam


class TestPluginBalticLivecam(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "https://balticlivecam.com/cameras/russia/sochi/primorsky-beach/",
            "https://balticlivecam.com/cameras/russia/sochi/sochi-panorama/",
            "https://www.balticlivecam.com/cameras/russia/sochi/primorsky-beach/",
            "https://www.balticlivecam.com/cameras/russia/sochi/sochi-panorama/",
        ]
        for url in should_match:
            self.assertTrue(BalticLivecam.can_handle_url(url))

        should_not_match = [
            "http://www.example.com/",
        ]
        for url in should_not_match:
            self.assertFalse(BalticLivecam.can_handle_url(url))

    def test_js_to_json_regex(self):
        test_data = """<script>
                var data = {
                    action: 'token',
                    id: 123,
                    embed:0,
                    referer: document
                    };</script>"""

        expected_data = {
            "action": "token",
            "embed": "0",
            "id": "123",
            "referer": "document",
        }

        self.assertDictEqual(BalticLivecam.js_to_json_regex(test_data), expected_data)
