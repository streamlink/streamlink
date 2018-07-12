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
            foo
            <script>
            var funkotron = { config: {
                "page": {
                    "content": {
                        "media": [
                            {
                                "sources": [
                                    {
                                        "file": "https://foo.bar/baz.mp4?qux"
                                    },
                                    {
                                        "file": "https://foo.bar/baz.m3u8?qux"
                                    }
                                ]
                            },
                            {
                                "sources": [
                                    {
                                        "file": "https://qux.baz/bar.mp4?foo"
                                    },
                                    {
                                        "file": "https://qux.baz/bar.m3u8?foo"
                                    }
                                ]
                            }
                        ]
                    }
                }
            }}
            </script>
            bar
        """)
        self.assertEqual(hls_url, "https://foo.bar/baz.m3u8?qux", "Finds the correct HLS live URL")

    def test_validate_vod(self):
        hls_url = Welt._schema_vod.validate("""
            {
                "urlWithToken": "https://foo.bar/baz.m3u8?qux"
            }
        """)
        self.assertEqual(hls_url, "https://foo.bar/baz.m3u8?qux", "Finds the correct HLS VOD URL")
