import json

from streamlink.plugins.tiktok import TikTok
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTikTok(PluginCanHandleUrl):
    __plugin__ = TikTok

    should_match_groups = [
        (("live", "https://www.tiktok.com/@LIVE"), {"channel": "LIVE"}),
        (("live", "https://www.tiktok.com/@LIVE/live"), {"channel": "LIVE"}),
        (("video", "https://www.tiktok.com/@VIDEO/video/0123456789"), {"channel": "VIDEO", "id": "0123456789"}),
    ]

    should_not_match = [
        "https://www.tiktok.com",
    ]


def test_get_streams_live(session, requests_mock):
    def stream_data(data):
        return json.dumps({"data": data})

    def endpoint(codec, bitrate, **urls):
        return {
            **urls,
            "sdk_params": json.dumps({"VCodec": codec, "vbitrate": bitrate}),
        }

    requests_mock.get(
        TikTok._URL_API_LIVE,
        json={
            "statusCode": 0,
            "data": {
                "liveRoom": {
                    "status": 2,
                    "streamId": "1234",
                    "title": "Live title",
                    "streamData": {
                        "pull_data": {
                            "stream_data": stream_data({
                                "hd": {
                                    "main": endpoint(
                                        "h264",
                                        1_800_000,
                                        hls="https://example.com/h264/hd/main.m3u8",
                                        flv="https://example.com/h264/hd/main.flv",
                                        cmaf="https://example.com/h264/hd/main.mpd",
                                    ),
                                    "backup": endpoint(
                                        "h264",
                                        1_800_000,
                                        hls="https://example.com/h264/hd/backup.m3u8",
                                    ),
                                },
                                "ao": {
                                    "main": endpoint("h264", 0, flv="https://example.com/h264/ao/main.flv"),
                                },
                            }),
                        },
                    },
                    "hevcStreamData": {
                        "pull_data": {
                            "stream_data": stream_data({
                                "origin": {
                                    "main": endpoint("h264", 0, flv="https://example.com/origin/main.m3u8"),
                                },
                                "uhd_60": {
                                    "main": endpoint("h265", 4_000_000, flv="https://example.com/h265/uhd60/main.m3u8"),
                                },
                                "hd": {
                                    "main": endpoint("h265", 1_350_000, flv="https://example.com/h265/hd/main.m3u8"),
                                },
                                "sd": {
                                    "main": endpoint("hevc", 1_000_000, flv="https://example.com/h265/sd/main.flv"),
                                },
                            }),
                        },
                    },
                },
            },
        },
    )

    plugin = TikTok(session, "https://www.tiktok.com/@LIVE/live")
    streams = plugin.streams()

    assert plugin.id == "1234"
    assert plugin.author == "LIVE"
    assert plugin.title == "Live title"

    assert list(streams.keys()) == [
        "h264_ao",
        "h265_sd",
        "h264_hd",
        "h265_hd",
        "h265_uhd_60",
        "h264_origin",
        "worst",
        "best",
    ]
    assert streams["worst"] is streams["h265_sd"]
    assert streams["best"] is streams["h264_origin"]

    request = requests_mock.request_history[0]
    assert request.qs == {
        "aid": ["1988"],
        "sourcetype": ["54"],
        "staletime": ["600000"],
        "uniqueid": ["live"],
    }
