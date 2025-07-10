import unittest
from unittest.mock import MagicMock, call, patch

import pytest

from streamlink.plugins.kick import Kick, KickHLSStream, KickHLSStreamReader, KickHLSStreamWriter
from tests.mixins.stream_hls import EventedHLSStreamWriter, Playlist, Segment, TestMixinStreamHLS
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlKick(PluginCanHandleUrl):
    __plugin__ = Kick

    should_match_groups = [
        (
            ("live", "https://kick.com/LIVE_CHANNEL"),
            {"channel": "LIVE_CHANNEL"},
        ),
        (
            ("vod", "https://kick.com/video/VIDEO_ID"),
            {"vod": "VIDEO_ID"},
        ),
        (
            ("vod", "https://kick.com/VIDEO_CHANNEL/videos/VIDEO_ID"),
            {"vod": "VIDEO_ID"},
        ),
        (
            ("clip", "https://kick.com/CLIP_CHANNEL?clip=CLIP_ID&foo=bar"),
            {"channel": "CLIP_CHANNEL", "clip": "CLIP_ID"},
        ),
        (
            ("clip", "https://kick.com/CLIP_CHANNEL/clips/CLIP_ID?foo=bar"),
            {"channel": "CLIP_CHANNEL", "clip": "CLIP_ID"},
        ),
        (
            ("clip", "https://kick.com/CLIP_CHANNEL/clips/CLIP_ID?clip=CLIP_ID_FROM_QUERY_STRING&foo=bar"),
            {"channel": "CLIP_CHANNEL", "clip": "CLIP_ID"},
        ),
    ]


class SegmentPrefetch(Segment):
    def build(self, namespace):
        return "#EXT-X-PREFETCH:{0}".format(self.url(namespace))


class _KickHLSStreamWriter(EventedHLSStreamWriter, KickHLSStreamWriter):
    pass


class _KickHLSStreamReader(KickHLSStreamReader):
    __writer__ = _KickHLSStreamWriter


class _KickHLSStream(KickHLSStream):
    __reader__ = _KickHLSStreamReader


@patch("streamlink.stream.hls.HLSStreamWorker.wait", MagicMock(return_value=True))
class TestKickHLSStream(TestMixinStreamHLS, unittest.TestCase):
    __stream__ = _KickHLSStream
    stream: KickHLSStream

    def get_session(self, *args, **kwargs):
        session = super().get_session(*args, **kwargs)
        session.set_option("hls-live-edge", 4)

        return session

    @patch("streamlink.plugins.kick.log")
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
            call("Low latency streaming (HLS live edge: 2)"),
        ]

    @patch("streamlink.plugins.kick.log")
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
        assert mock_log.info.mock_calls == []

    @patch("streamlink.plugins.kick.log")
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
            call("Low latency streaming (HLS live edge: 2)"),
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
