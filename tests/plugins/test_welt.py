from streamlink.plugins.welt import Welt
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlWelt(PluginCanHandleUrl):
    __plugin__ = Welt

    should_match = [
        "http://welt.de",
        "http://welt.de/",
        "http://welt.de/tv-programm-live-stream/",
        "http://www.welt.de",
        "http://www.welt.de/",
        "http://www.welt.de/tv-programm-live-stream/",
        "https://welt.de",
        "https://welt.de/",
        "https://welt.de/tv-programm-live-stream/",
        "https://www.welt.de",
        "https://www.welt.de/",
        "https://www.welt.de/tv-programm-live-stream/",
    ]


class TestPluginWelt:
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
        assert hls_url == "https://foo.bar/baz.m3u8?qux"
