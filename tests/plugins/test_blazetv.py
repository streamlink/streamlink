from streamlink.plugins.blazetv import BlazeTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlBlazeTV(PluginCanHandleUrl):
    __plugin__ = BlazeTV

    should_match = [
        "https://blaze.tv/live",
        "https://www.blaze.tv/live",
        "https://watch.blaze.tv/live",
        "https://www.blaze.tv/watch/replay/12345",
    ]

    should_match_groups = [
        (
            "https://blaze.tv/live",
            {"is_live": "live"},
        ),
        (
            "https://www.blaze.tv/live",
            {"is_live": "live"},
        ),
        (
            "https://watch.blaze.tv/live",
            {"is_live": "live"},
        ),
        (
            "https://www.blaze.tv/watch/replay/12345",
            {},
        ),
    ]

    should_not_match = [
        "https://blaze.tv/",
        "https://www.blaze.tv/",
        "https://www.blaze.tv/watch",
    ]


class TestBlazeTV:
    def test_live(self, session, requests_mock):
        url = "https://blaze.tv/live"
        api_url = "https://v2-streams-elb.simplestreamcdn.com/api/live/stream/553"
        master_url = "https://example.com/live/master.m3u8"

        requests_mock.get(
            url,
            text="""
                <html>
                    <body>
                        <div
                            data-type="live"
                            data-key="test-key"
                            data-uvid="553"
                            data-expiry="1790675966"
                            data-token="test-token"
                        ></div>
                    </body>
                </html>
            """,
        )

        requests_mock.post(
            f"{api_url}?key=test-key&platform=chrome",
            complete_qs=True,
            json={
                "response": {
                    "stream": master_url,
                },
            },
        )

        requests_mock.get(
            master_url,
            text="""#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=640x360
https://example.com/live/360p.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2000000,RESOLUTION=1280x720
https://example.com/live/720p.m3u8
""",
        )

        plugin = BlazeTV(session, url)
        streams = plugin.streams()

        assert "360p" in streams
        assert "720p" in streams

        post_request = next(request for request in requests_mock.request_history if request.method == "POST")

        assert post_request.headers["Accept"] == "application/json"
        assert post_request.headers["Token"] == "test-token"
        assert post_request.headers["Token-Expiry"] == "1790675966"
        assert post_request.headers["Userid"] == "123456"
        assert post_request.headers["Uvid"] == "553"
