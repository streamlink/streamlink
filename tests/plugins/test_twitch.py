import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, call, patch

import requests_mock

from streamlink import Streamlink
from streamlink.plugins.twitch import Twitch, TwitchHLSStream, TwitchHLSStreamReader, TwitchHLSStreamWriter
from tests.mixins.stream_hls import EventedHLSStreamWriter, Playlist, Segment as _Segment, Tag, TestMixinStreamHLS
from tests.plugins import PluginCanHandleUrl
from tests.resources import text


class TestPluginCanHandleUrlTwitch(PluginCanHandleUrl):
    __plugin__ = Twitch

    should_match_groups = [
        ("https://www.twitch.tv/twitch", {
            "subdomain": "www",
            "channel": "twitch",
        }),
        ("https://www.twitch.tv/videos/150942279", {
            "subdomain": "www",
            "videos_id": "150942279",
        }),
        ("https://clips.twitch.tv/ObservantBenevolentCarabeefPhilosoraptor", {
            "subdomain": "clips",
            "channel": "ObservantBenevolentCarabeefPhilosoraptor",
        }),
        ("https://www.twitch.tv/weplaydota/clip/FurryIntelligentDonutAMPEnergyCherry-akPRxv7Y3w58WmFq", {
            "subdomain": "www",
            "channel": "weplaydota",
            "clip_name": "FurryIntelligentDonutAMPEnergyCherry-akPRxv7Y3w58WmFq",
        }),
        ("https://www.twitch.tv/twitch/video/292713971", {
            "subdomain": "www",
            "channel": "twitch",
            "video_id": "292713971",
        }),
        ("https://www.twitch.tv/twitch/v/292713971", {
            "subdomain": "www",
            "channel": "twitch",
            "video_id": "292713971",
        }),
    ]

    should_not_match = [
        'https://www.twitch.tv',
        'https://www.twitch.tv/',
    ]


DATETIME_BASE = datetime(2000, 1, 1, 0, 0, 0, 0)
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


class TagDateRangeAd(Tag):
    def __init__(self, start=DATETIME_BASE, duration=1, id="stitched-ad-1234", classname="twitch-stitched-ad", custom=None):
        attrs = {
            "ID": self.val_quoted_string(id),
            "CLASS": self.val_quoted_string(classname),
            "START-DATE": self.val_quoted_string(start.strftime(DATETIME_FORMAT)),
            "DURATION": duration
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
            super().build(namespace)
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


def test_stream_weight():
    session = Streamlink()
    plugin = Twitch(session, "http://twitch.tv/foo")

    with text("hls/test_master_twitch_vod.m3u8") as fh:
        playlist = fh.read()
    with requests_mock.Mocker() as mocker:
        mocker.register_uri(requests_mock.ANY, requests_mock.ANY, exc=requests_mock.exceptions.InvalidRequest)
        mocker.request(method="GET", url="http://mocked/master.m3u8", text=playlist)
        streams = TwitchHLSStream.parse_variant_playlist(session, "http://mocked/master.m3u8")
    with patch.object(plugin, "_get_streams", return_value=streams):
        data = plugin.streams()

    assert list(data.keys()) == ["audio", "160p30", "360p30", "480p30", "720p30", "720p60", "source", "worst", "best"]
    assert data["best"] is data["source"]
    assert data["worst"] is data["160p30"]


@patch("streamlink.stream.hls.HLSStreamWorker.wait", MagicMock(return_value=True))
class TestTwitchHLSStream(TestMixinStreamHLS, unittest.TestCase):
    __stream__ = _TwitchHLSStream

    def get_session(self, options=None, disable_ads=False, low_latency=False):
        session = super().get_session(options)
        session.set_option("hls-live-edge", 4)
        session.set_plugin_option("twitch", "disable-ads", disable_ads)
        session.set_plugin_option("twitch", "low-latency", low_latency)

        return session

    def test_hls_disable_ads_daterange_unknown(self):
        daterange = TagDateRangeAd(start=DATETIME_BASE, duration=1, id="foo", classname="bar", custom=None)
        thread, segments = self.subject([
            Playlist(0, [daterange, Segment(0), Segment(1)], end=True)
        ], disable_ads=True, low_latency=False)

        self.await_write(2)
        self.assertEqual(self.await_read(read_all=True), self.content(segments), "Doesn't filter out segments")
        self.assertTrue(all(self.called(s) for s in segments.values()), "Downloads all segments")

    def test_hls_disable_ads_daterange_by_class(self):
        daterange = TagDateRangeAd(start=DATETIME_BASE, duration=1, id="foo", classname="twitch-stitched-ad", custom=None)
        thread, segments = self.subject([
            Playlist(0, [daterange, Segment(0), Segment(1)], end=True)
        ], disable_ads=True, low_latency=False)

        self.await_write(2)
        self.assertEqual(self.await_read(read_all=True), segments[1].content, "Filters out ad segments")
        self.assertTrue(all(self.called(s) for s in segments.values()), "Downloads all segments")

    def test_hls_disable_ads_daterange_by_id(self):
        daterange = TagDateRangeAd(start=DATETIME_BASE, duration=1, id="stitched-ad-1234", classname="/", custom=None)
        thread, segments = self.subject([
            Playlist(0, [daterange, Segment(0), Segment(1)], end=True)
        ], disable_ads=True, low_latency=False)

        self.await_write(2)
        self.assertEqual(self.await_read(read_all=True), segments[1].content, "Filters out ad segments")
        self.assertTrue(all(self.called(s) for s in segments.values()), "Downloads all segments")

    def test_hls_disable_ads_daterange_by_attr(self):
        daterange = TagDateRangeAd(start=DATETIME_BASE, duration=1, id="foo", classname="/", custom={"X-TV-TWITCH-AD-URL": "/"})
        thread, segments = self.subject([
            Playlist(0, [daterange, Segment(0), Segment(1)], end=True)
        ], disable_ads=True, low_latency=False)

        self.await_write(2)
        self.assertEqual(self.await_read(read_all=True), segments[1].content, "Filters out ad segments")
        self.assertTrue(all(self.called(s) for s in segments.values()), "Downloads all segments")

    @patch("streamlink.plugins.twitch.log")
    def test_hls_disable_ads_has_preroll(self, mock_log):
        daterange = TagDateRangeAd(duration=4)
        thread, segments = self.subject([
            Playlist(0, [daterange, Segment(0), Segment(1)]),
            Playlist(2, [daterange, Segment(2), Segment(3)]),
            Playlist(4, [Segment(4), Segment(5)], end=True)
        ], disable_ads=True, low_latency=False)

        self.await_write(6)
        self.assertEqual(
            self.await_read(read_all=True),
            self.content(segments, cond=lambda s: s.num >= 4),
            "Filters out preroll ad segments"
        )
        self.assertTrue(all(self.called(s) for s in segments.values()), "Downloads all segments")

        self.assertEqual(mock_log.info.mock_calls, [
            call("Will skip ad segments"),
            call("Waiting for pre-roll ads to finish, be patient")
        ])

    @patch("streamlink.plugins.twitch.log")
    def test_hls_disable_ads_has_midstream(self, mock_log):
        daterange = TagDateRangeAd(start=DATETIME_BASE + timedelta(seconds=2), duration=2)
        thread, segments = self.subject([
            Playlist(0, [Segment(0), Segment(1)]),
            Playlist(2, [daterange, Segment(2), Segment(3)]),
            Playlist(4, [Segment(4), Segment(5)], end=True)
        ], disable_ads=True, low_latency=False)

        self.await_write(6)
        self.assertEqual(
            self.await_read(read_all=True),
            self.content(segments, cond=lambda s: s.num != 2 and s.num != 3),
            "Filters out mid-stream ad segments"
        )
        self.assertTrue(all(self.called(s) for s in segments.values()), "Downloads all segments")

        self.assertEqual(mock_log.info.mock_calls, [
            call("Will skip ad segments")
        ])

    @patch("streamlink.plugins.twitch.log")
    def test_hls_no_disable_ads_has_preroll(self, mock_log):
        daterange = TagDateRangeAd(duration=2)
        thread, segments = self.subject([
            Playlist(0, [daterange, Segment(0), Segment(1)]),
            Playlist(2, [Segment(2), Segment(3)], end=True)
        ], disable_ads=False, low_latency=False)

        self.await_write(4)
        self.assertEqual(
            self.await_read(read_all=True),
            self.content(segments),
            "Doesn't filter out segments"
        )
        self.assertTrue(all(self.called(s) for s in segments.values()), "Downloads all segments")

        self.assertEqual(mock_log.info.mock_calls, [], "Doesn't log anything")

    @patch("streamlink.plugins.twitch.log")
    def test_hls_low_latency_has_prefetch(self, mock_log):
        thread, segments = self.subject([
            Playlist(0, [Segment(0), Segment(1), Segment(2), Segment(3), SegmentPrefetch(4), SegmentPrefetch(5)]),
            Playlist(4, [Segment(4), Segment(5), Segment(6), Segment(7), SegmentPrefetch(8), SegmentPrefetch(9)], end=True)
        ], disable_ads=False, low_latency=True)

        self.assertEqual(2, self.session.options.get("hls-live-edge"))
        self.assertEqual(True, self.session.options.get("hls-segment-stream-data"))

        self.await_write(6)
        self.assertEqual(
            self.await_read(read_all=True),
            self.content(segments, cond=lambda s: s.num >= 4),
            "Skips first four segments due to reduced live-edge"
        )
        self.assertFalse(any(self.called(s) for s in segments.values() if s.num < 4), "Doesn't download old segments")

        self.assertTrue(all(self.called(s) for s in segments.values() if s.num >= 4), "Downloads all remaining segments")

        self.assertEqual(mock_log.info.mock_calls, [
            call("Low latency streaming (HLS live edge: 2)")
        ])

    @patch("streamlink.plugins.twitch.log")
    def test_hls_no_low_latency_has_prefetch(self, mock_log):
        thread, segments = self.subject([
            Playlist(0, [Segment(0), Segment(1), Segment(2), Segment(3), SegmentPrefetch(4), SegmentPrefetch(5)]),
            Playlist(4, [Segment(4), Segment(5), Segment(6), Segment(7), SegmentPrefetch(8), SegmentPrefetch(9)], end=True)
        ], disable_ads=False, low_latency=False)

        self.assertEqual(4, self.session.options.get("hls-live-edge"))
        self.assertEqual(False, self.session.options.get("hls-segment-stream-data"))

        self.await_write(8)
        self.assertEqual(
            self.await_read(read_all=True),
            self.content(segments, cond=lambda s: s.num < 8),
            "Ignores prefetch segments"
        )
        self.assertTrue(all(self.called(s) for s in segments.values() if s.num <= 7), "Ignores prefetch segments")

        self.assertFalse(any(self.called(s) for s in segments.values() if s.num > 7), "Ignores prefetch segments")

        self.assertEqual(mock_log.info.mock_calls, [], "Doesn't log anything")

    @patch("streamlink.plugins.twitch.log")
    def test_hls_low_latency_no_prefetch(self, mock_log):
        self.subject([
            Playlist(0, [Segment(0), Segment(1), Segment(2), Segment(3)]),
            Playlist(4, [Segment(4), Segment(5), Segment(6), Segment(7)], end=True)
        ], disable_ads=False, low_latency=True)

        self.assertTrue(self.session.get_plugin_option("twitch", "low-latency"))
        self.assertFalse(self.session.get_plugin_option("twitch", "disable-ads"))

        self.await_write(6)
        self.await_read(read_all=True)
        self.assertEqual(mock_log.info.mock_calls, [
            call("Low latency streaming (HLS live edge: 2)"),
            call("This is not a low latency stream")
        ])

    @patch("streamlink.plugins.twitch.log")
    def test_hls_low_latency_has_prefetch_has_preroll(self, mock_log):
        daterange = TagDateRangeAd(duration=4)
        thread, segments = self.subject([
            Playlist(0, [daterange, Segment(0), Segment(1), Segment(2), Segment(3)]),
            Playlist(4, [Segment(4), Segment(5), Segment(6), Segment(7), SegmentPrefetch(8), SegmentPrefetch(9)], end=True)
        ], disable_ads=False, low_latency=True)

        self.await_write(8)
        self.assertEqual(
            self.await_read(read_all=True),
            self.content(segments, cond=lambda s: s.num > 1),
            "Skips first two segments due to reduced live-edge"
        )
        self.assertFalse(any(self.called(s) for s in segments.values() if s.num < 2), "Skips first two preroll segments")

        self.assertTrue(all(self.called(s) for s in segments.values() if s.num >= 2), "Downloads all remaining segments")

        self.assertEqual(mock_log.info.mock_calls, [
            call("Low latency streaming (HLS live edge: 2)")
        ])

    @patch("streamlink.plugins.twitch.log")
    def test_hls_low_latency_has_prefetch_disable_ads_has_preroll(self, mock_log):
        daterange = TagDateRangeAd(duration=4)
        self.subject([
            Playlist(0, [daterange, Segment(0), Segment(1), Segment(2), Segment(3)]),
            Playlist(4, [Segment(4), Segment(5), Segment(6), Segment(7), SegmentPrefetch(8), SegmentPrefetch(9)], end=True)
        ], disable_ads=True, low_latency=True)

        self.await_write(8)
        self.await_read(read_all=True)
        self.assertEqual(mock_log.info.mock_calls, [
            call("Will skip ad segments"),
            call("Low latency streaming (HLS live edge: 2)"),
            call("Waiting for pre-roll ads to finish, be patient")
        ])

    @patch("streamlink.plugins.twitch.log")
    def test_hls_low_latency_has_prefetch_disable_ads_no_preroll_with_prefetch_ads(self, mock_log):
        # segment 1 has a shorter duration, to mess with the extrapolation of the prefetch start times
        # segments 3-6 are ads
        Seg, Pre = Segment, SegmentPrefetch
        ads = [
            Tag("EXT-X-DISCONTINUITY"),
            TagDateRangeAd(start=DATETIME_BASE + timedelta(seconds=3), duration=4),
        ]
        # noinspection PyTypeChecker
        thread, segments = self.subject([
            # regular stream data with prefetch segments
            Playlist(0, [Seg(0), Seg(1, duration=0.5), Pre(2), Pre(3)]),
            # three prefetch segments, one regular (2) and two ads (3 and 4)
            Playlist(1, [Seg(1, duration=0.5), Pre(2)] + ads + [Pre(3), Pre(4)]),
            # all prefetch segments are gone once regular prefetch segments have shifted
            Playlist(2, [Seg(2, duration=1.5)] + ads + [Seg(3), Seg(4), Seg(5)]),
            # still no prefetch segments while ads are playing
            Playlist(3, ads + [Seg(3), Seg(4), Seg(5), Seg(6)]),
            # new prefetch segments on the first regular segment occurrence
            Playlist(4, ads + [Seg(4), Seg(5), Seg(6), Seg(7), Pre(8), Pre(9)]),
            Playlist(5, ads + [Seg(5), Seg(6), Seg(7), Seg(8), Pre(9), Pre(10)]),
            Playlist(6, ads + [Seg(6), Seg(7), Seg(8), Seg(9), Pre(10), Pre(11)]),
            Playlist(7, [Seg(7), Seg(8), Seg(9), Seg(10), Pre(11), Pre(12)], end=True),
        ], disable_ads=True, low_latency=True)

        self.await_write(11)
        content = self.await_read(read_all=True)
        assert content == self.content(segments, cond=lambda s: 2 <= s.num <= 3 or 7 <= s.num)
        assert mock_log.info.mock_calls == [
            call("Will skip ad segments"),
            call("Low latency streaming (HLS live edge: 2)"),
        ]

    @patch("streamlink.plugins.twitch.log")
    def test_hls_low_latency_no_prefetch_disable_ads_has_preroll(self, mock_log):
        daterange = TagDateRangeAd(duration=4)
        self.subject([
            Playlist(0, [daterange, Segment(0), Segment(1), Segment(2), Segment(3)]),
            Playlist(4, [Segment(4), Segment(5), Segment(6), Segment(7)], end=True)
        ], disable_ads=True, low_latency=True)

        self.await_write(6)
        self.await_read(read_all=True)
        self.assertEqual(mock_log.info.mock_calls, [
            call("Will skip ad segments"),
            call("Low latency streaming (HLS live edge: 2)"),
            call("Waiting for pre-roll ads to finish, be patient"),
            call("This is not a low latency stream")
        ])

    def test_hls_low_latency_no_ads_reload_time(self):
        self.subject([
            Playlist(0, [Segment(0, duration=5), Segment(1, duration=7), Segment(2, duration=11), SegmentPrefetch(3)], end=True)
        ], low_latency=True)

        self.await_write(4)
        self.await_read(read_all=True)
        self.assertEqual(self.thread.reader.worker.playlist_reload_time, 23 / 3)


class TestTwitchMetadata(unittest.TestCase):
    def setUp(self):
        self.mock = requests_mock.Mocker()
        self.mock.register_uri(requests_mock.ANY, requests_mock.ANY, exc=requests_mock.exceptions.InvalidRequest)
        self.mock.start()

    def tearDown(self):
        self.mock.stop()

    @staticmethod
    def subject(url):
        session = Streamlink()
        plugin = Twitch(session, url)
        return plugin.get_id(), plugin.get_author(), plugin.get_category(), plugin.get_title()

    def mock_request_channel(self, data=True):
        return self.mock.post(
            "https://gql.twitch.tv/gql",
            json=[
                {"data": {"userOrError": {"userDoesNotExist": "error"} if not data else {
                    "displayName": "channel name"
                }}},
                {"data": {"user": None if not data else {
                    "lastBroadcast": {
                        "title": "channel status"
                    },
                    "stream": {
                        "id": "stream id",
                        "game": {
                            "name": "channel game"
                        }
                    }
                }}}
            ]
        )

    def mock_request_video(self, data=True):
        return self.mock.post(
            "https://gql.twitch.tv/gql",
            json={"data": {"video": None if not data else {
                "id": "video id",
                "title": "video title",
                "game": {
                    "displayName": "video game"
                },
                "owner": {
                    "displayName": "channel name"
                }
            }}}
        )

    def mock_request_clip(self, data=True):
        return self.mock.post(
            "https://gql.twitch.tv/gql",
            json=[
                {"data": {
                    "clip": None if not data else {
                        "id": "clip id",
                        "broadcaster": {
                            "displayName": "channel name"
                        },
                        "game": {
                            "name": "game name"
                        }
                    }
                }},
                {"data": {
                    "clip": None if not data else {
                        "title": "clip title"
                    }
                }}
            ]
        )

    def test_metadata_channel(self):
        mock = self.mock_request_channel()
        _id, author, category, title = self.subject("https://twitch.tv/foo")
        self.assertEqual(_id, "stream id")
        self.assertEqual(author, "channel name")
        self.assertEqual(category, "channel game")
        self.assertEqual(title, "channel status")
        self.assertEqual(mock.call_count, 1)
        self.assertEqual(mock.request_history[0].json(), [
            {
                "operationName": "ChannelShell",
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "c3ea5a669ec074a58df5c11ce3c27093fa38534c94286dc14b68a25d5adcbf55"
                    }
                },
                "variables": {
                    "login": "foo",
                    "lcpVideosEnabled": False
                }
            },
            {
                "operationName": "StreamMetadata",
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "059c4653b788f5bdb2f5a2d2a24b0ddc3831a15079001a3d927556a96fb0517f"
                    }
                },
                "variables": {
                    "channelLogin": "foo"
                }
            }
        ])

    def test_metadata_channel_no_data(self):
        self.mock_request_channel(data=False)
        _id, author, category, title = self.subject("https://twitch.tv/foo")
        self.assertEqual(_id, None)
        self.assertEqual(author, None)
        self.assertEqual(category, None)
        self.assertEqual(title, None)

    def test_metadata_video(self):
        mock = self.mock_request_video()
        _id, author, category, title = self.subject("https://twitch.tv/videos/1337")
        self.assertEqual(_id, "video id")
        self.assertEqual(author, "channel name")
        self.assertEqual(category, "video game")
        self.assertEqual(title, "video title")
        self.assertEqual(mock.call_count, 1)
        self.assertEqual(
            mock.request_history[0].json(),
            {
                "operationName": "VideoMetadata",
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "cb3b1eb2f2d2b2f65b8389ba446ec521d76c3aa44f5424a1b1d235fe21eb4806"
                    }
                },
                "variables": {
                    "channelLogin": "",
                    "videoID": "1337"
                }
            }
        )

    def test_metadata_video_no_data(self):
        self.mock_request_video(data=False)
        _id, author, category, title = self.subject("https://twitch.tv/videos/1337")
        self.assertEqual(_id, None)
        self.assertEqual(author, None)
        self.assertEqual(category, None)
        self.assertEqual(title, None)

    def test_metadata_clip(self):
        mock = self.mock_request_clip()
        _id, author, category, title = self.subject("https://clips.twitch.tv/foo")
        self.assertEqual(_id, "clip id")
        self.assertEqual(author, "channel name")
        self.assertEqual(category, "game name")
        self.assertEqual(title, "clip title")
        self.assertEqual(mock.call_count, 1)
        self.assertEqual(mock.request_history[0].json(), [
            {
                "operationName": "ClipsView",
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "4480c1dcc2494a17bb6ef64b94a5213a956afb8a45fe314c66b0d04079a93a8f"
                    }
                },
                "variables": {
                    "slug": "foo"
                }
            },
            {
                "operationName": "ClipsTitle",
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "f6cca7f2fdfbfc2cecea0c88452500dae569191e58a265f97711f8f2a838f5b4"
                    }
                },
                "variables": {
                    "slug": "foo"
                }
            }
        ])

    def test_metadata_clip_no_data(self):
        self.mock_request_clip(data=False)
        _id, author, category, title = self.subject("https://clips.twitch.tv/foo")
        self.assertEqual(_id, None)
        self.assertEqual(author, None)
        self.assertEqual(category, None)
        self.assertEqual(title, None)


@patch("streamlink.plugins.twitch.log")
class TestTwitchReruns(unittest.TestCase):
    log_call = call("Reruns were disabled by command line option")

    def subject(self, **params):
        with patch("streamlink.plugins.twitch.TwitchAPI.stream_metadata") as mock:
            mock.return_value = None if params.pop("offline", False) else {"type": params.pop("stream_type", "live")}
            session = Streamlink()
            plugin = Twitch(session, "https://www.twitch.tv/foo")
            plugin.options.set("disable-reruns", params.pop("disable", True))

            return plugin._check_for_rerun()

    def test_disable_reruns_live(self, mock_log):
        self.assertFalse(self.subject())
        self.assertNotIn(self.log_call, mock_log.info.call_args_list)

    def test_disable_reruns_not_live(self, mock_log):
        self.assertTrue(self.subject(stream_type="rerun"))
        self.assertIn(self.log_call, mock_log.info.call_args_list)

    def test_disable_reruns_offline(self, mock_log):
        self.assertFalse(self.subject(offline=True))
        self.assertNotIn(self.log_call, mock_log.info.call_args_list)

    def test_enable_reruns(self, mock_log):
        self.assertFalse(self.subject(stream_type="rerun", disable=False))
        self.assertNotIn(self.log_call, mock_log.info.call_args_list)
