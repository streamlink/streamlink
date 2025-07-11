from __future__ import annotations

import json
import unittest
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, call, patch
from urllib.parse import parse_qsl, urlparse

import pytest
import requests_mock as rm

from streamlink import Streamlink
from streamlink.exceptions import NoStreamsError, PluginError
from streamlink.options import Options
from streamlink.plugin.api import useragents
from streamlink.plugins.twitch import Twitch, TwitchAPI, TwitchHLSStream, TwitchHLSStreamReader, TwitchHLSStreamWriter
from tests.mixins.stream_hls import EventedHLSStreamWriter, Playlist, Segment as _Segment, Tag, TestMixinStreamHLS
from tests.plugins import PluginCanHandleUrl
from tests.resources import text


class TestPluginCanHandleUrlTwitch(PluginCanHandleUrl):
    __plugin__ = Twitch

    should_match_groups = [
        (
            ("live", "https://www.twitch.tv/CHANNELNAME"),
            {
                "channel": "CHANNELNAME",
            },
        ),
        (
            ("live", "https://www.twitch.tv/CHANNELNAME?"),
            {
                "channel": "CHANNELNAME",
            },
        ),
        (
            ("live", "https://www.twitch.tv/CHANNELNAME/"),
            {
                "channel": "CHANNELNAME",
            },
        ),
        (
            ("live", "https://www.twitch.tv/CHANNELNAME/?"),
            {
                "channel": "CHANNELNAME",
            },
        ),
        (
            ("vod", "https://www.twitch.tv/videos/1963401646"),
            {
                "video_id": "1963401646",
            },
        ),
        (
            ("vod", "https://www.twitch.tv/dota2ti/v/1963401646"),
            {
                "video_id": "1963401646",
            },
        ),
        (
            ("vod", "https://www.twitch.tv/dota2ti/video/1963401646"),
            {
                "video_id": "1963401646",
            },
        ),
        (
            ("vod", "https://www.twitch.tv/videos/1963401646?t=1h23m45s"),
            {
                "video_id": "1963401646",
            },
        ),
        (
            ("clip", "https://clips.twitch.tv/GoodEndearingPassionfruitPMSTwin-QfRLYDPKlscgqt-4"),
            {
                "clip_id": "GoodEndearingPassionfruitPMSTwin-QfRLYDPKlscgqt-4",
            },
        ),
        (
            ("clip", "https://www.twitch.tv/clip/GoodEndearingPassionfruitPMSTwin-QfRLYDPKlscgqt-4"),
            {
                "clip_id": "GoodEndearingPassionfruitPMSTwin-QfRLYDPKlscgqt-4",
            },
        ),
        (
            ("clip", "https://www.twitch.tv/lirik/clip/GoodEndearingPassionfruitPMSTwin-QfRLYDPKlscgqt-4"),
            {
                "clip_id": "GoodEndearingPassionfruitPMSTwin-QfRLYDPKlscgqt-4",
            },
        ),
        (
            ("clip", "https://twitch.tv/papaplatte/clip/SmellyDeadMomBloodTrail-WWr5gMxd0pe0BAge"),
            {
                "clip_id": "SmellyDeadMomBloodTrail-WWr5gMxd0pe0BAge",
            },
        ),
        (
            ("player", "https://player.twitch.tv/?parent=twitch.tv&channel=CHANNELNAME"),
            {},
        ),
        (
            ("player", "https://player.twitch.tv/?parent=twitch.tv&video=1963401646"),
            {},
        ),
        (
            ("player", "https://player.twitch.tv/?parent=twitch.tv&video=1963401646&t=1h23m45s"),
            {},
        ),
    ]

    should_not_match = [
        "https://www.twitch.tv",
        "https://www.twitch.tv/",
        "https://www.twitch.tv/videos/",
        "https://www.twitch.tv/dota2ti/v",
        "https://www.twitch.tv/dota2ti/video/",
        "https://clips.twitch.tv/",
        "https://www.twitch.tv/clip/",
        "https://www.twitch.tv/lirik/clip/",
        "https://player.twitch.tv/",
        "https://player.twitch.tv/?",
    ]


DATETIME_BASE = datetime(2000, 1, 1, 0, 0, 0, 0, timezone.utc)
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


class TagDateRangeAd(Tag):
    def __init__(self, start=DATETIME_BASE, duration=1, attrid="stitched-ad-1234", classname="twitch-stitched-ad", custom=None):
        attrs = {
            "ID": self.val_quoted_string(attrid),
            "CLASS": self.val_quoted_string(classname),
            "START-DATE": self.val_quoted_string(start.strftime(DATETIME_FORMAT)),
            "DURATION": duration,
        }
        if custom is not None:
            attrs.update(**{key: self.val_quoted_string(value) for (key, value) in custom.items()})
        super().__init__("EXT-X-DATERANGE", attrs)


class Segment(_Segment):
    def __init__(self, num, title="live", *args, **kwargs):
        super().__init__(num, title, *args, **kwargs)
        self.date = DATETIME_BASE + timedelta(seconds=num)

    def build(self, namespace):
        return "#EXT-X-PROGRAM-DATE-TIME:{0}\n{1}".format(
            self.date.strftime(DATETIME_FORMAT),
            super().build(namespace),
        )


class SegmentPrefetch(Segment):
    def build(self, namespace):
        return "#EXT-X-TWITCH-PREFETCH:{0}".format(self.url(namespace))


class _TwitchHLSStreamWriter(EventedHLSStreamWriter, TwitchHLSStreamWriter):
    pass


class _TwitchHLSStreamReader(TwitchHLSStreamReader):
    __writer__ = _TwitchHLSStreamWriter


class _TwitchHLSStream(TwitchHLSStream):
    __reader__ = _TwitchHLSStreamReader


def test_stream_weight(requests_mock: rm.Mocker, session: Streamlink):
    plugin = Twitch(session, "http://twitch.tv/foo")

    with text("hls/test_master_twitch_vod.m3u8") as fh:
        playlist = fh.read()

    requests_mock.request(method="GET", url="http://mocked/master.m3u8", text=playlist)
    streams = TwitchHLSStream.parse_variant_playlist(session, "http://mocked/master.m3u8")

    with patch.object(plugin, "_get_streams", return_value=streams):
        data = plugin.streams()

    assert list(data.keys()) == ["audio", "160p30", "360p30", "480p30", "720p30", "720p60", "source", "worst", "best"]
    assert data["best"] is data["source"]
    assert data["worst"] is data["160p30"]


@patch("streamlink.stream.hls.HLSStreamWorker.wait", MagicMock(return_value=True))
class TestTwitchHLSStream(TestMixinStreamHLS, unittest.TestCase):
    __stream__ = _TwitchHLSStream
    stream: TwitchHLSStream

    def get_session(self, *args, **kwargs):
        session = super().get_session(*args, **kwargs)
        session.set_option("hls-live-edge", 4)

        return session

    def test_hls_daterange_unknown(self):
        daterange = TagDateRangeAd(
            start=DATETIME_BASE,
            duration=1,
            attrid="foo",
            classname="bar",
            custom=None,
        )

        segments = self.subject(
            [
                Playlist(0, [daterange, Segment(0), Segment(1)], end=True),
            ],
            streamoptions={"low_latency": False},
        )

        self.await_write(2)
        data = self.await_read(read_all=True)
        assert data == self.content(segments), "Doesn't filter out segments"
        assert all(self.called(s) for s in segments.values()), "Downloads all segments"

    def test_hls_daterange_by_class(self):
        daterange = TagDateRangeAd(
            start=DATETIME_BASE,
            duration=1,
            attrid="foo",
            classname="twitch-stitched-ad",
            custom=None,
        )

        segments = self.subject(
            [
                Playlist(0, [daterange, Segment(0), Segment(1)], end=True),
            ],
            streamoptions={"low_latency": False},
        )

        self.await_write(2)
        data = self.await_read(read_all=True)
        assert data == segments[1].content, "Filters out ad segments"
        assert all(self.called(s) for s in segments.values()), "Downloads all segments"

    def test_hls_daterange_by_id(self):
        daterange = TagDateRangeAd(
            start=DATETIME_BASE,
            duration=1,
            attrid="stitched-ad-1234",
            classname="/",
            custom=None,
        )

        segments = self.subject(
            [
                Playlist(0, [daterange, Segment(0), Segment(1)], end=True),
            ],
            streamoptions={"low_latency": False},
        )

        self.await_write(2)
        data = self.await_read(read_all=True)
        assert data == segments[1].content, "Filters out ad segments"
        assert all(self.called(s) for s in segments.values()), "Downloads all segments"

    @patch("streamlink.plugins.twitch.log")
    def test_hls_has_preroll(self, mock_log):
        daterange = TagDateRangeAd(
            duration=4,
            custom={"X-TV-TWITCH-AD-ROLL-TYPE": "PREROLL"},
        )
        segments = self.subject(
            [
                Playlist(0, [daterange, Segment(0), Segment(1)]),
                Playlist(2, [daterange, Segment(2), Segment(3)]),
                Playlist(4, [Segment(4), Segment(5)], end=True),
            ],
            streamoptions={"low_latency": False},
        )

        self.await_write(6)
        data = self.await_read(read_all=True)
        assert data == self.content(segments, cond=lambda s: s.num >= 4), "Filters out preroll ad segments"
        assert all(self.called(s) for s in segments.values()), "Downloads all segments"
        assert mock_log.info.mock_calls == [
            call("Will skip ad segments"),
            call("Waiting for pre-roll ads to finish, be patient"),
            call("Detected advertisement break of 4 seconds"),
        ]

    @patch("streamlink.plugins.twitch.log")
    def test_hls_has_midroll(self, mock_log):
        daterange = TagDateRangeAd(
            start=DATETIME_BASE + timedelta(seconds=2),
            duration=2,
            custom={"X-TV-TWITCH-AD-ROLL-TYPE": "MIDROLL", "X-TV-TWITCH-AD-COMMERCIAL-ID": "123"},
        )
        segments = self.subject(
            [
                Playlist(0, [Segment(0), Segment(1)]),
                Playlist(2, [daterange, Segment(2), Segment(3)]),
                Playlist(4, [Segment(4), Segment(5)], end=True),
            ],
            streamoptions={"low_latency": False},
        )

        self.await_write(6)
        data = self.await_read(read_all=True)
        assert data == self.content(segments, cond=lambda s: s.num != 2 and s.num != 3), "Filters out mid-stream ad segments"
        assert all(self.called(s) for s in segments.values()), "Downloads all segments"
        assert mock_log.info.mock_calls == [
            call("Will skip ad segments"),
            call("Detected advertisement break of 2 seconds"),
        ]

    @patch("streamlink.plugins.twitch.log")
    def test_hls_has_preroll_and_midroll(self, mock_log):
        ads1a = TagDateRangeAd(
            start=DATETIME_BASE,
            duration=2,
            custom={"X-TV-TWITCH-AD-ROLL-TYPE": "PREROLL"},
        )
        ads1b = TagDateRangeAd(
            start=DATETIME_BASE,
            duration=1,
        )
        ads2 = TagDateRangeAd(
            start=DATETIME_BASE + timedelta(seconds=4),
            duration=4,
            custom={
                "X-TV-TWITCH-AD-ROLL-TYPE": "MIDROLL",
                "X-TV-TWITCH-AD-COMMERCIAL-ID": "123",
            },
        )
        ads3 = TagDateRangeAd(
            start=DATETIME_BASE + timedelta(seconds=8),
            duration=1,
            custom={
                "X-TV-TWITCH-AD-ROLL-TYPE": "MIDROLL",
                "X-TV-TWITCH-AD-COMMERCIAL-ID": "456",
                "X-TV-TWITCH-AD-POD-FILLED-DURATION": ".9",
            },
        )
        segments = self.subject(
            [
                Playlist(0, [ads1a, ads1b, Segment(0)]),
                Playlist(1, [ads1a, ads1b, Segment(1)]),
                Playlist(2, [Segment(2), Segment(3)]),
                Playlist(4, [ads2, Segment(4), Segment(5)]),
                Playlist(6, [ads2, Segment(6), Segment(7)]),
                Playlist(8, [ads3, Segment(8), Segment(9)], end=True),
            ],
            streamoptions={"low_latency": False},
        )

        self.await_write(10)
        data = self.await_read(read_all=True)
        assert data == self.content(segments, cond=lambda s: s.num not in (0, 1, 4, 5, 6, 7, 8)), "Filters out all ad segments"
        assert all(self.called(s) for s in segments.values()), "Downloads all segments"
        assert mock_log.info.mock_calls == [
            call("Will skip ad segments"),
            call("Waiting for pre-roll ads to finish, be patient"),
            call("Detected advertisement break of 2 seconds"),
            call("Detected advertisement break of 4 seconds"),
            call("Detected advertisement break of 1 second"),
        ]

    @patch("streamlink.plugins.twitch.log")
    def test_hls_low_latency_has_prefetch(self, mock_log):
        segments = self.subject(
            [
                Playlist(0, [Segment(0), Segment(1), Segment(2), Segment(3), SegmentPrefetch(4), SegmentPrefetch(5)]),
                Playlist(4, [Segment(4), Segment(5), Segment(6), Segment(7), SegmentPrefetch(8), SegmentPrefetch(9)], end=True),
            ],
            streamoptions={"low_latency": True},
        )

        assert self.session.options.get("hls-live-edge") == 2
        assert self.session.options.get("hls-segment-stream-data")

        self.await_write(6)
        data = self.await_read(read_all=True)
        assert data == self.content(segments, cond=lambda s: s.num >= 4), "Skips first four segments due to reduced live-edge"
        assert not any(self.called(s) for s in segments.values() if s.num < 4), "Doesn't download old segments"
        assert all(self.called(s) for s in segments.values() if s.num >= 4), "Downloads all remaining segments"
        assert mock_log.info.mock_calls == [
            call("Will skip ad segments"),
            call("Low latency streaming (HLS live edge: 2)"),
        ]

    @patch("streamlink.plugins.twitch.log")
    def test_hls_no_low_latency_has_prefetch(self, mock_log):
        segments = self.subject(
            [
                Playlist(0, [Segment(0), Segment(1), Segment(2), Segment(3), SegmentPrefetch(4), SegmentPrefetch(5)]),
                Playlist(4, [Segment(4), Segment(5), Segment(6), Segment(7), SegmentPrefetch(8), SegmentPrefetch(9)], end=True),
            ],
            streamoptions={"low_latency": False},
        )

        assert self.session.options.get("hls-live-edge") == 4
        assert not self.session.options.get("hls-segment-stream-data")

        self.await_write(8)
        data = self.await_read(read_all=True)
        assert data == self.content(segments, cond=lambda s: s.num < 8), "Ignores prefetch segments"
        assert all(self.called(s) for s in segments.values() if s.num <= 7), "Ignores prefetch segments"
        assert not any(self.called(s) for s in segments.values() if s.num > 7), "Ignores prefetch segments"
        assert mock_log.info.mock_calls == [
            call("Will skip ad segments"),
        ]

    @patch("streamlink.plugins.twitch.log")
    def test_hls_low_latency_no_prefetch(self, mock_log):
        self.subject(
            [
                Playlist(0, [Segment(0), Segment(1), Segment(2), Segment(3)]),
                Playlist(4, [Segment(4), Segment(5), Segment(6), Segment(7)], end=True),
            ],
            streamoptions={"low_latency": True},
        )

        assert self.stream.low_latency

        self.await_write(6)
        self.await_read(read_all=True)
        assert mock_log.info.mock_calls == [
            call("Will skip ad segments"),
            call("Low latency streaming (HLS live edge: 2)"),
            call("This is not a low latency stream"),
        ]

    @patch("streamlink.plugins.twitch.log")
    def test_hls_low_latency_has_prefetch_has_preroll(self, mock_log):
        daterange = TagDateRangeAd(
            duration=4,
            custom={"X-TV-TWITCH-AD-ROLL-TYPE": "PREROLL"},
        )
        self.subject(
            [
                Playlist(0, [daterange, Segment(0), Segment(1), Segment(2), Segment(3)]),
                Playlist(4, [Segment(4), Segment(5), Segment(6), Segment(7), SegmentPrefetch(8), SegmentPrefetch(9)], end=True),
            ],
            streamoptions={"low_latency": True},
        )

        self.await_write(8)
        self.await_read(read_all=True)
        assert mock_log.info.mock_calls == [
            call("Will skip ad segments"),
            call("Low latency streaming (HLS live edge: 2)"),
            call("Waiting for pre-roll ads to finish, be patient"),
            call("Detected advertisement break of 4 seconds"),
        ]

    @patch("streamlink.plugins.twitch.log")
    def test_hls_low_latency_has_prefetch_no_preroll_with_prefetch_ads(self, mock_log):
        # segment 1 has a shorter duration, to mess with the extrapolation of the prefetch start times
        # segments 3-6 are ads
        Seg, Pre = Segment, SegmentPrefetch
        ads = [
            Tag("EXT-X-DISCONTINUITY"),
            TagDateRangeAd(
                start=DATETIME_BASE + timedelta(seconds=3),
                duration=4,
                custom={"X-TV-TWITCH-AD-ROLL-TYPE": "MIDROLL"},
            ),
        ]
        tls = Tag("EXT-X-TWITCH-LIVE-SEQUENCE", 7)
        # noinspection PyTypeChecker
        segments = self.subject(
            [
                # regular stream data with prefetch segments
                Playlist(0, [Seg(0), Seg(1, duration=0.5), Pre(2), Pre(3)]),
                # three prefetch segments, one regular (2) and two ads (3 and 4)
                Playlist(1, [Seg(1, duration=0.5), Pre(2), *ads, Pre(3), Pre(4)]),
                # all prefetch segments are gone once regular prefetch segments have shifted
                Playlist(2, [Seg(2, duration=1.5), *ads, Seg(3), Seg(4), Seg(5)]),
                # still no prefetch segments while ads are playing
                Playlist(3, [*ads, Seg(3), Seg(4), Seg(5), Seg(6)]),
                # new prefetch segments on the first regular segment occurrence
                Playlist(4, [*ads, Seg(4), Seg(5), Seg(6), tls, Seg(7), Pre(8), Pre(9)]),
                Playlist(5, [*ads, Seg(5), Seg(6), tls, Seg(7), Seg(8), Pre(9), Pre(10)]),
                Playlist(6, [*ads, Seg(6), tls, Seg(7), Seg(8), Seg(9), Pre(10), Pre(11)]),
                Playlist(7, [Seg(7), Seg(8), Seg(9), Seg(10), Pre(11), Pre(12)], end=True),
            ],
            streamoptions={"low_latency": True},
        )

        self.await_write(11)
        data = self.await_read(read_all=True)
        assert data == self.content(segments, cond=lambda s: 2 <= s.num <= 3 or 7 <= s.num)
        assert mock_log.info.mock_calls == [
            call("Will skip ad segments"),
            call("Low latency streaming (HLS live edge: 2)"),
            call("Detected advertisement break of 4 seconds"),
        ]

    @patch("streamlink.plugins.twitch.log")
    def test_hls_low_latency_no_prefetch_has_preroll(self, mock_log):
        daterange = TagDateRangeAd(
            duration=4,
            custom={"X-TV-TWITCH-AD-ROLL-TYPE": "PREROLL"},
        )
        self.subject(
            [
                Playlist(0, [daterange, Segment(0), Segment(1), Segment(2), Segment(3)]),
                Playlist(4, [Segment(4), Segment(5), Segment(6), Segment(7)], end=True),
            ],
            streamoptions={"low_latency": True},
        )

        self.await_write(6)
        self.await_read(read_all=True)
        assert mock_log.info.mock_calls == [
            call("Will skip ad segments"),
            call("Low latency streaming (HLS live edge: 2)"),
            call("Waiting for pre-roll ads to finish, be patient"),
            call("Detected advertisement break of 4 seconds"),
            call("This is not a low latency stream"),
        ]

    def test_hls_low_latency_no_ads_reload_time(self):
        Seg, SegPre = Segment, SegmentPrefetch
        self.subject(
            [
                Playlist(0, [Seg(0, duration=5), Seg(1, duration=7), Seg(2, duration=11), SegPre(3)], end=True),
            ],
            streamoptions={"low_latency": True},
        )

        self.await_write(4)
        self.await_read(read_all=True)
        assert self.thread.reader.worker.playlist_reload_time == pytest.approx(23 / 3)

    @patch("streamlink.stream.hls.hls.log")
    def test_hls_prefetch_after_discontinuity(self, mock_log):
        segments = self.subject(
            [
                Playlist(0, [Segment(0), Segment(1)]),
                Playlist(2, [Segment(2), Segment(3), Tag("EXT-X-DISCONTINUITY"), SegmentPrefetch(4), SegmentPrefetch(5)]),
                Playlist(6, [Segment(6), Segment(7)], end=True),
            ],
            streamoptions={"low_latency": True},
        )

        self.await_write(8)
        assert self.await_read(read_all=True) == self.content(segments, cond=lambda seg: seg.num not in (4, 5))
        assert mock_log.warning.mock_calls == [
            call("Encountered a stream discontinuity. This is unsupported and will result in incoherent output data."),
        ]

    @patch("streamlink.stream.hls.hls.log")
    def test_hls_ignored_discontinuity(self, mock_log):
        Seg, Pre = Segment, SegmentPrefetch
        discontinuity = Tag("EXT-X-DISCONTINUITY")
        tls = Tag("EXT-X-TWITCH-LIVE-SEQUENCE", 1234)  # value is irrelevant
        segments = self.subject(
            [
                Playlist(0, [Seg(0), discontinuity, Seg(1)]),
                Playlist(2, [Seg(2), Seg(3), discontinuity, Seg(4), Seg(5)]),
                Playlist(6, [Seg(6), Seg(7), discontinuity, tls, Pre(8), Pre(9)]),
                Playlist(10, [Seg(10), Seg(11), discontinuity, tls, Pre(12), discontinuity, tls, Pre(13)], end=True),
            ],
            streamoptions={"low_latency": True},
        )

        self.await_write(14)
        assert self.await_read(read_all=True) == self.content(segments)
        assert mock_log.warning.mock_calls == []


class TestUsherService:
    @pytest.fixture(autouse=True)
    def caplog(self, caplog: pytest.LogCaptureFixture):
        caplog.set_level(1, "streamlink.plugins.twitch")
        return caplog

    @pytest.fixture()
    def plugin(self, request: pytest.FixtureRequest, session: Streamlink):
        return Twitch(
            session,
            "https://twitch.tv/twitch",
            options=Options(getattr(request, "param", {})),
        )

    @pytest.fixture()
    def endpoint(self, request: pytest.FixtureRequest, caplog: pytest.LogCaptureFixture, plugin: Twitch):
        param = getattr(request, "param", {})
        service = param.get("service", "channel")
        args = param.get("args", ("twitch",))

        token = {
            "expires": 9876543210,
            "channel": "twitch",
            "channel_id": 123,
            "user_id": 456,
            "user_ip": "127.0.0.1",
            "adblock": False,
            "geoblock_reason": "",
            "hide_ads": False,
            "server_ads": True,
            "show_ads": True,
        }

        return getattr(plugin.usher, service)(*args, token=json.dumps(token), sig="tokensignature")

    @pytest.mark.parametrize(
        ("endpoint", "expected_path", "logs"),
        [
            pytest.param(
                {"service": "channel", "args": ("TWITCH",)},
                "/api/channel/hls/twitch.m3u8",
                [
                    (
                        "streamlink.plugins.twitch",
                        "debug",
                        "{'adblock': False, 'geoblock_reason': '', 'hide_ads': False, 'server_ads': True, 'show_ads': True}",
                    ),
                ],
                id="channel",
            ),
            pytest.param(
                {"service": "video", "args": ("1234567890",)},
                "/vod/1234567890",
                [],
                id="video",
            ),
        ],
        indirect=["endpoint"],
    )
    def test_service(self, caplog: pytest.LogCaptureFixture, endpoint: str, expected_path: str, logs: list):
        url = urlparse(endpoint)
        assert url.path == expected_path

        qs = dict(parse_qsl(url.query))
        assert qs.get("token")
        assert qs.get("sig")

        assert [(r.name, r.levelname, r.message) for r in caplog.get_records(when="setup")] == logs


class TestTwitchAPIAccessToken:
    @pytest.fixture(autouse=True)
    def _client_integrity_token(self, monkeypatch: pytest.MonkeyPatch):
        mock_client_integrity_token = Mock(return_value=("device-id", "client-integrity-token"))
        monkeypatch.setattr(Twitch, "_client_integrity_token", mock_client_integrity_token)

    @pytest.fixture()
    def plugin(self, request: pytest.FixtureRequest, session: Streamlink):
        options = Options(getattr(request, "param", {}))

        return Twitch(session, "https://twitch.tv/channelname", options)

    @pytest.fixture()
    def mock(self, request: pytest.FixtureRequest, requests_mock: rm.Mocker):
        mock = requests_mock.post("https://gql.twitch.tv/gql", **getattr(request, "param", {"json": {}}))
        yield mock
        assert mock.call_count > 0
        payload = mock.last_request.json()  # type: ignore[union-attr]
        assert tuple(sorted(payload.keys())) == ("extensions", "operationName", "variables")
        assert payload.get("operationName") == "PlaybackAccessToken"
        assert payload.get("extensions") == {
            "persistedQuery": {
                "sha256Hash": "0828119ded1c13477966434e15800ff57ddacf13ba1911c129dc2200705b0712",
                "version": 1,
            },
        }

    @pytest.fixture()
    def _assert_live(self, mock: rm.Mocker):
        yield
        assert mock.last_request.json().get("variables") == {  # type: ignore[union-attr]
            "isLive": True,
            "isVod": False,
            "login": "channelname",
            "vodID": "",
            "playerType": "embed",
        }

    @pytest.fixture()
    def _assert_vod(self, mock: rm.Mocker):
        yield
        assert mock.last_request.json().get("variables") == {  # type: ignore[union-attr]
            "isLive": False,
            "isVod": True,
            "login": "",
            "vodID": "vodid",
            "playerType": "embed",
        }

    @pytest.mark.parametrize(
        ("plugin", "exp_headers", "exp_variables"),
        [
            (
                {},
                {"Client-ID": TwitchAPI.CLIENT_ID},
                {
                    "isLive": True,
                    "isVod": False,
                    "login": "channelname",
                    "vodID": "",
                    "playerType": "embed",
                },
            ),
            (
                {
                    "api-header": [
                        ("Authorization", "invalid data"),
                        ("Authorization", "OAuth 0123456789abcdefghijklmnopqrst"),
                    ],
                    "access-token-param": [
                        ("specialVariable", "specialValue"),
                        ("playerType", "frontpage"),
                    ],
                },
                {
                    "Client-ID": TwitchAPI.CLIENT_ID,
                    "Authorization": "OAuth 0123456789abcdefghijklmnopqrst",
                },
                {
                    "isLive": True,
                    "isVod": False,
                    "login": "channelname",
                    "vodID": "",
                    "playerType": "frontpage",
                    "specialVariable": "specialValue",
                },
            ),
        ],
        indirect=["plugin"],
    )
    def test_plugin_options(self, plugin: Twitch, mock: rm.Mocker, exp_headers: dict, exp_variables: dict):
        with pytest.raises(PluginError):
            plugin._access_token(True, "channelname")
        requestheaders = dict(mock.last_request._request.headers)  # type: ignore[union-attr]
        for header in plugin.session.http.headers.keys():
            del requestheaders[header]
        del requestheaders["Content-Type"]
        del requestheaders["Content-Length"]
        assert requestheaders == exp_headers
        assert mock.last_request.json().get("variables") == exp_variables  # type: ignore[union-attr]

    @pytest.mark.parametrize(
        ("session", "mock"),
        [
            pytest.param(
                {},
                {"json": {"data": {"streamPlaybackAccessToken": {"value": '{"channel":"foo"}', "signature": "sig"}}}},
                id="no-custom-user-agent",
            ),
            pytest.param(
                {"http-headers": {"User-Agent": "foo"}},
                {"json": {"data": {"streamPlaybackAccessToken": {"value": '{"channel":"foo"}', "signature": "sig"}}}},
                id="custom-user-agent",
            ),
        ],
        indirect=True,
    )
    def test_user_agent(self, plugin: Twitch, mock: rm.Mocker):
        plugin._access_token(True, "channelname")
        assert len(mock.request_history) > 0
        assert mock.request_history[0]._request.headers["User-Agent"] == useragents.DEFAULT

    @pytest.mark.usefixtures("_assert_live")
    @pytest.mark.parametrize(
        ("plugin", "mock"),
        [
            pytest.param(
                {
                    "force-client-integrity": False,
                },
                {
                    "json": {"data": {"streamPlaybackAccessToken": {"value": '{"channel":"foo"}', "signature": "sig"}}},
                },
                id="no-force-client-integrity",
            ),
            pytest.param(
                {
                    "force-client-integrity": True,
                },
                {
                    "json": {"data": {"streamPlaybackAccessToken": {"value": '{"channel":"foo"}', "signature": "sig"}}},
                },
                id="force-client-integrity",
            ),
        ],
        indirect=True,
    )
    def test_live_success(self, plugin: Twitch, mock: rm.Mocker):
        data = plugin._access_token(True, "channelname")
        assert data == ("sig", '{"channel":"foo"}', [])
        assert len(mock.request_history) == 1

    @pytest.mark.usefixtures("_assert_live")
    @pytest.mark.parametrize(
        "mock",
        [
            {
                "json": {"data": {"streamPlaybackAccessToken": None}},
            },
        ],
        indirect=True,
    )
    def test_live_failure(self, plugin: Twitch, mock: rm.Mocker):
        with pytest.raises(NoStreamsError):
            plugin._access_token(True, "channelname")
        assert len(mock.request_history) == 1, "Only gets the access token once when the channel is offline"

    @pytest.mark.usefixtures("_assert_vod")
    @pytest.mark.parametrize(
        "mock",
        [
            {
                "json": {"data": {"videoPlaybackAccessToken": {"value": '{"channel":"foo"}', "signature": "sig"}}},
            },
        ],
        indirect=True,
    )
    def test_vod_success(self, plugin: Twitch, mock: rm.Mocker):
        data = plugin._access_token(False, "vodid")
        assert data == ("sig", '{"channel":"foo"}', [])

    @pytest.mark.usefixtures("_assert_vod")
    @pytest.mark.parametrize(
        "mock",
        [
            {
                "json": {"data": {"videoPlaybackAccessToken": None}},
            },
        ],
        indirect=True,
    )
    def test_vod_failure(self, plugin: Twitch, mock: rm.Mocker):
        with pytest.raises(NoStreamsError):
            plugin._access_token(False, "vodid")
        assert len(mock.request_history) == 1, "Only gets the access token once when the VOD doesn't exist"

    @pytest.mark.usefixtures("_assert_live")
    @pytest.mark.parametrize(
        ("plugin", "mock"),
        [
            (
                {
                    "api-header": [("Authorization", "OAuth invalid-token")],
                },
                {
                    "status_code": 401,
                    "json": {"error": "Unauthorized", "status": 401, "message": 'The "Authorization" token is invalid.'},
                },
            ),
        ],
        indirect=True,
    )
    def test_auth_failure(self, plugin: Twitch, mock: rm.Mocker):
        with pytest.raises(PluginError, match=r'^Unauthorized: The "Authorization" token is invalid\.$'):
            plugin._access_token(True, "channelname")
        assert len(mock.request_history) == 2, "Always tries again on error, with integrity-token on second attempt"

        headers: dict = mock.request_history[0]._request.headers
        assert headers["Authorization"] == "OAuth invalid-token"
        assert "Device-Id" not in headers
        assert "Client-Integrity" not in headers

        headers = mock.request_history[1]._request.headers
        assert headers["Authorization"] == "OAuth invalid-token"
        assert headers["Device-Id"] == "device-id"
        assert headers["Client-Integrity"] == "client-integrity-token"

    @pytest.mark.usefixtures("_assert_live")
    @pytest.mark.parametrize(
        ("plugin", "mock"),
        [
            (
                {
                    "force-client-integrity": False,
                    "api-header": [("Authorization", "OAuth invalid-token")],
                },
                {
                    "response_list": [
                        {
                            "status_code": 401,
                            "json": {"errors": [{"message": "failed integrity check"}]},
                        },
                        {
                            "json": {"data": {"streamPlaybackAccessToken": {"value": '{"channel":"foo"}', "signature": "sig"}}},
                        },
                    ],
                },
            ),
        ],
        indirect=True,
    )
    def test_integrity_check_not_forced(self, plugin: Twitch, mock: rm.Mocker):
        data = plugin._access_token(True, "channelname")
        assert data == ("sig", '{"channel":"foo"}', [])
        assert len(mock.request_history) == 2, "Always tries again on error, with integrity-token on second attempt"

        headers: dict = mock.request_history[0]._request.headers
        assert headers["Authorization"] == "OAuth invalid-token"
        assert "Device-Id" not in headers
        assert "Client-Integrity" not in headers

        headers = mock.request_history[1]._request.headers
        assert headers["Authorization"] == "OAuth invalid-token"
        assert headers["Device-Id"] == "device-id"
        assert headers["Client-Integrity"] == "client-integrity-token"

    @pytest.mark.usefixtures("_assert_live")
    @pytest.mark.parametrize(
        ("plugin", "mock"),
        [
            (
                {
                    "force-client-integrity": True,
                    "api-header": [("Authorization", "OAuth invalid-token")],
                },
                {
                    "response_list": [
                        {
                            "json": {"data": {"streamPlaybackAccessToken": {"value": '{"channel":"foo"}', "signature": "sig"}}},
                        },
                    ],
                },
            ),
        ],
        indirect=True,
    )
    def test_integrity_check_forced(self, plugin: Twitch, mock: rm.Mocker):
        data = plugin._access_token(True, "channelname")
        assert data == ("sig", '{"channel":"foo"}', [])
        assert len(mock.request_history) == 1

        headers: dict = mock.request_history[0]._request.headers
        assert headers["Authorization"] == "OAuth invalid-token"
        assert headers["Device-Id"] == "device-id"
        assert headers["Client-Integrity"] == "client-integrity-token"

    @pytest.mark.usefixtures("_assert_vod")
    @pytest.mark.parametrize(
        ("plugin", "mock"),
        [
            (
                {
                    "force-client-integrity": True,
                    "api-header": [("Authorization", "OAuth invalid-token")],
                },
                {
                    "response_list": [
                        {
                            "json": {"data": {"videoPlaybackAccessToken": {"value": '{"channel":"foo"}', "signature": "sig"}}},
                        },
                    ],
                },
            ),
        ],
        indirect=True,
    )
    def test_integrity_check_vod(self, plugin: Twitch, mock: rm.Mocker):
        data = plugin._access_token(False, "vodid")
        assert data == ("sig", '{"channel":"foo"}', [])
        assert len(mock.request_history) == 1

        headers: dict = mock.request_history[0]._request.headers
        assert headers["Authorization"] == "OAuth invalid-token"
        assert "Device-Id" not in headers
        assert "Client-Integrity" not in headers


class TestTwitchHLSMultivariantResponse:
    @pytest.fixture()
    def plugin(self, request: pytest.FixtureRequest, requests_mock: rm.Mocker, session: Streamlink):
        requests_mock.get("mock://multivariant", **getattr(request, "param", {}))
        return Twitch(session, "https://twitch.tv/channelname")

    @pytest.mark.parametrize(
        ("plugin", "streamid", "raises", "streams", "log"),
        [
            pytest.param(
                {"text": "#EXTM3U\n"},
                "123",
                nullcontext(),
                {},
                [],
                id="success",
            ),
            pytest.param(
                {"text": "Not an HLS playlist"},
                "123",
                pytest.raises(PluginError),
                {},
                [],
                id="invalid HLS playlist",
            ),
            pytest.param(
                {
                    "status_code": 404,
                    "json": [
                        {
                            "url": "mock://multivariant",
                            "error": "twirp error not_found: transcode does not exist",
                            "error_code": "transcode_does_not_exist",
                            "type": "error",
                        },
                    ],
                },
                None,
                nullcontext(),
                None,
                [],
                id="offline",
            ),
            pytest.param(
                {
                    "status_code": 403,
                    "json": [
                        {
                            "url": "mock://multivariant",
                            "error": "Content Restricted In Region",
                            "error_code": "content_geoblocked",
                            "type": "error",
                        },
                    ],
                },
                "123",
                nullcontext(),
                None,
                [("streamlink.plugins.twitch", "error", "Content Restricted In Region")],
                id="geo restriction",
            ),
            pytest.param(
                {
                    "status_code": 404,
                    "text": "Not found",
                },
                "123",
                nullcontext(),
                None,
                [],
                id="non-json error response",
            ),
        ],
        indirect=["plugin"],
    )
    def test_multivariant_response(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        plugin: Twitch,
        streamid: str | None,
        raises: nullcontext,
        streams: dict | None,
        log: list,
    ):
        caplog.set_level("error", "streamlink.plugins.twitch")
        monkeypatch.setattr(plugin, "get_id", Mock(return_value=streamid))
        with raises:
            assert plugin._get_hls_streams("mock://multivariant", []) == streams
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == log


class TestTwitchMetadata:
    @pytest.fixture()
    def metadata(self, request: pytest.FixtureRequest, session: Streamlink):
        url = getattr(request, "param", "")
        plugin = Twitch(session, url)

        return plugin.get_id(), plugin.get_author(), plugin.get_category(), plugin.get_title()

    @pytest.fixture()
    def mock_request_channel(self, request: pytest.FixtureRequest, requests_mock: rm.Mocker):
        data = getattr(request, "param", True)

        return requests_mock.post(
            "https://gql.twitch.tv/gql",
            json=[
                {
                    "data": {
                        "userOrError": {"userDoesNotExist": "error"}
                        if not data
                        else {
                            "displayName": "channel name",
                        },
                    },
                },
                {
                    "data": {
                        "user": None
                        if not data
                        else {
                            "lastBroadcast": {
                                "title": "channel status",
                            },
                            "stream": {
                                "id": "stream id",
                                "game": {
                                    "name": "channel game",
                                },
                            },
                        },
                    },
                },
            ],
        )

    @pytest.fixture()
    def mock_request_video(self, request: pytest.FixtureRequest, requests_mock: rm.Mocker):
        data = getattr(request, "param", True)

        return requests_mock.post(
            "https://gql.twitch.tv/gql",
            json={
                "data": {
                    "video": None
                    if not data
                    else {
                        "id": "video id",
                        "title": "video title",
                        "game": {
                            "displayName": "video game",
                        },
                        "owner": {
                            "displayName": "channel name",
                        },
                    },
                },
            },
        )

    @pytest.fixture()
    def mock_request_clip(self, request: pytest.FixtureRequest, requests_mock: rm.Mocker):
        data = getattr(request, "param", True)

        return requests_mock.post(
            "https://gql.twitch.tv/gql",
            json=[
                {
                    "data": {
                        "clip": None
                        if not data
                        else {
                            "id": "clip id",
                            "broadcaster": {
                                "displayName": "channel name",
                            },
                            "game": {
                                "name": "game name",
                            },
                        },
                    },
                },
                {
                    "data": {
                        "clip": None
                        if not data
                        else {
                            "title": "clip title",
                        },
                    },
                },
            ],
        )

    @pytest.mark.parametrize(("mock_request_channel", "metadata"), [(True, "https://twitch.tv/foo")], indirect=True)
    def test_metadata_channel(self, mock_request_channel, metadata):
        assert metadata == ("stream id", "channel name", "channel game", "channel status")
        assert mock_request_channel.call_count == 1
        assert mock_request_channel.request_history[0].json() == [
            {
                "operationName": "ChannelShell",
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "c3ea5a669ec074a58df5c11ce3c27093fa38534c94286dc14b68a25d5adcbf55",
                    },
                },
                "variables": {
                    "login": "foo",
                    "lcpVideosEnabled": False,
                },
            },
            {
                "operationName": "StreamMetadata",
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "059c4653b788f5bdb2f5a2d2a24b0ddc3831a15079001a3d927556a96fb0517f",
                    },
                },
                "variables": {
                    "channelLogin": "foo",
                },
            },
        ]

    @pytest.mark.parametrize(("mock_request_channel", "metadata"), [(False, "https://twitch.tv/foo")], indirect=True)
    def test_metadata_channel_no_data(self, mock_request_channel, metadata):
        assert metadata == (None, None, None, None)
        assert mock_request_channel.call_count == 1

    @pytest.mark.parametrize(("mock_request_video", "metadata"), [(True, "https://twitch.tv/videos/1337")], indirect=True)
    def test_metadata_video(self, mock_request_video, metadata):
        assert metadata == ("video id", "channel name", "video game", "video title")
        assert mock_request_video.call_count == 1
        assert mock_request_video.request_history[0].json() == {
            "operationName": "VideoMetadata",
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "cb3b1eb2f2d2b2f65b8389ba446ec521d76c3aa44f5424a1b1d235fe21eb4806",
                },
            },
            "variables": {
                "channelLogin": "",
                "videoID": "1337",
            },
        }

    @pytest.mark.parametrize(("mock_request_video", "metadata"), [(False, "https://twitch.tv/videos/1337")], indirect=True)
    def test_metadata_video_no_data(self, mock_request_video, metadata):
        assert metadata == (None, None, None, None)
        assert mock_request_video.call_count == 1

    @pytest.mark.parametrize(("mock_request_clip", "metadata"), [(True, "https://clips.twitch.tv/foo")], indirect=True)
    def test_metadata_clip(self, mock_request_clip, metadata):
        assert metadata == ("clip id", "channel name", "game name", "clip title")
        assert mock_request_clip.call_count == 1
        assert mock_request_clip.request_history[0].json() == [
            {
                "operationName": "ClipsView",
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "4480c1dcc2494a17bb6ef64b94a5213a956afb8a45fe314c66b0d04079a93a8f",
                    },
                },
                "variables": {
                    "slug": "foo",
                },
            },
            {
                "operationName": "ClipsTitle",
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "f6cca7f2fdfbfc2cecea0c88452500dae569191e58a265f97711f8f2a838f5b4",
                    },
                },
                "variables": {
                    "slug": "foo",
                },
            },
        ]

    @pytest.mark.parametrize(("mock_request_clip", "metadata"), [(False, "https://clips.twitch.tv/foo")], indirect=True)
    def test_metadata_clip_no_data(self, mock_request_clip, metadata):
        assert metadata == (None, None, None, None)
