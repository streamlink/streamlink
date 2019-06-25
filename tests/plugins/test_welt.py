import unittest

from streamlink.plugins.welt import Welt


class TestPluginWelt(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Welt.can_handle_url("http://welt.de"))
        self.assertTrue(Welt.can_handle_url("http://welt.de/"))
        self.assertTrue(Welt.can_handle_url("http://welt.de/tv-programm-live-stream/"))
        self.assertTrue(Welt.can_handle_url("http://www.welt.de"))
        self.assertTrue(Welt.can_handle_url("http://www.welt.de/"))
        self.assertTrue(Welt.can_handle_url("http://www.welt.de/tv-programm-live-stream/"))
        self.assertTrue(Welt.can_handle_url("https://welt.de"))
        self.assertTrue(Welt.can_handle_url("https://welt.de/"))
        self.assertTrue(Welt.can_handle_url("https://welt.de/tv-programm-live-stream/"))
        self.assertTrue(Welt.can_handle_url("https://www.welt.de"))
        self.assertTrue(Welt.can_handle_url("https://www.welt.de/"))
        self.assertTrue(Welt.can_handle_url("https://www.welt.de/tv-programm-live-stream/"))

        # shouldn't match
        self.assertFalse(Welt.can_handle_url("http://www.youtube.com/"))
        self.assertFalse(Welt.can_handle_url("http://youtube.com/"))

    def test_validate_live(self):
        hls_url = Welt._schema.validate("""
            <!DOCTYPE html><html><body>
            <script type="application/json" data-content="VideoPlayer.Config">
                {
                    "title": "foo",
                    "sources": [
                        {
                            "src": "https://foo.bar/baz.mp4?qux",
                            "extension": "mp4"
                        },
                        {
                            "src": "https://foo.bar/baz.m3u8?qux",
                            "extension": "m3u8"
                        }
                    ]
                }
            </script>
            </body></html>
        """)
        self.assertEqual(hls_url, "https://foo.bar/baz.m3u8?qux", "Finds the correct HLS live URL")
