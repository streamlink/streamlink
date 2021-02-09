import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, call, patch

import requests_mock

from streamlink import Streamlink
from streamlink.plugin import PluginError
from streamlink.plugins.twitch import Twitch, TwitchHLSStream, TwitchHLSStreamReader, TwitchHLSStreamWriter
from tests.mixins.stream_hls import EventedHLSStreamWriter, Playlist, Segment as _Segment, Tag, TestMixinStreamHLS
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTwitch(PluginCanHandleUrl):
    __plugin__ = Twitch

    should_match = [
        'https://www.twitch.tv/twitch',
        'https://www.twitch.tv/videos/150942279',
        'https://clips.twitch.tv/ObservantBenevolentCarabeefPhilosoraptor',
        'https://www.twitch.tv/twitch/video/292713971',
        'https://www.twitch.tv/twitch/v/292713971',
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
        self.assertTrue(all([self.called(s) for s in segments.values()]), "Downloads all segments")
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
        self.assertTrue(all([self.called(s) for s in segments.values()]), "Downloads all segments")
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
        self.assertTrue(all([self.called(s) for s in segments.values()]), "Downloads all segments")
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
        self.assertFalse(any([self.called(s) for s in segments.values() if s.num < 4]), "Doesn't download old segments")
        self.assertTrue(all([self.called(s) for s in segments.values() if s.num >= 4]), "Downloads all remaining segments")
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
        self.assertTrue(all([self.called(s) for s in segments.values() if s.num <= 7]), "Ignores prefetch segments")
        self.assertFalse(any([self.called(s) for s in segments.values() if s.num > 7]), "Ignores prefetch segments")
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
        self.assertFalse(any([self.called(s) for s in segments.values() if s.num < 2]), "Skips first two preroll segments")
        self.assertTrue(all([self.called(s) for s in segments.values() if s.num >= 2]), "Downloads all remaining segments")
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


class TestTwitchMetadata(unittest.TestCase):
    def setUp(self):
        self.mock = requests_mock.Mocker()
        self.mock.start()

    def tearDown(self):
        self.mock.stop()

    def subject(self, url):
        session = Streamlink()
        Twitch.bind(session, "tests.plugins.test_twitch")
        plugin = Twitch(url)
        return plugin.get_author(), plugin.get_title(), plugin.get_category()

    def subject_channel(self, data=True, failure=False):
        self.mock.get(
            "https://api.twitch.tv/kraken/users?login=foo",
            json={"users": [{"_id": 1234}]}
        )
        self.mock.get(
            "https://api.twitch.tv/kraken/streams/1234",
            status_code=200 if not failure else 404,
            json={"stream": None} if not data else {"stream": {
                "channel": {
                    "display_name": "channel name",
                    "status": "channel status",
                    "game": "channel game"
                }
            }}
        )
        return self.subject("https://twitch.tv/foo")

    def subject_video(self, data=True, failure=False):
        self.mock.get(
            "https://api.twitch.tv/kraken/videos/1337",
            status_code=200 if not failure else 404,
            json={} if not data else {
                "title": "video title",
                "game": "video game",
                "channel": {
                    "display_name": "channel name"
                }
            }
        )
        return self.subject("https://twitch.tv/videos/1337")

    def test_metadata_channel_exists(self):
        author, title, category = self.subject_channel()
        self.assertEqual(author, "channel name")
        self.assertEqual(title, "channel status")
        self.assertEqual(category, "channel game")

    def test_metadata_channel_missing(self):
        metadata = self.subject_channel(data=False)
        self.assertEqual(metadata, (None, None, None))

    def test_metadata_channel_invalid(self):
        with self.assertRaises(PluginError):
            self.subject_channel(failure=True)

    def test_metadata_video_exists(self):
        author, title, category = self.subject_video()
        self.assertEqual(author, "channel name")
        self.assertEqual(title, "video title")
        self.assertEqual(category, "video game")

    def test_metadata_video_missing(self):
        metadata = self.subject_video(data=False)
        self.assertEqual(metadata, (None, None, None))

    def test_metadata_video_invalid(self):
        with self.assertRaises(PluginError):
            self.subject_video(failure=True)


@patch("streamlink.plugins.twitch.log")
class TestTwitchHosting(unittest.TestCase):
    def subject(self, channel, hosts=None, disable=False):
        with requests_mock.Mocker() as mock:
            mock.get(
                "https://api.twitch.tv/kraken/users?login=foo",
                json={"users": [{"_id": 1}]}
            )
            if hosts is None:
                mock.get("https://tmi.twitch.tv/hosts", json={})
            else:
                mock.get(
                    "https://tmi.twitch.tv/hosts",
                    [{"json": {
                        "hosts": [dict(
                            host_id=host_id,
                            target_id=target_id,
                            target_login=target_login,
                            target_display_name=target_display_name
                        )]}
                      } for host_id, target_id, target_login, target_display_name in hosts]
                )

            session = Streamlink()
            Twitch.bind(session, "tests.plugins.test_twitch")
            plugin = Twitch("https://twitch.tv/{0}".format(channel))
            plugin.options.set("disable-hosting", disable)

            res = plugin._switch_to_hosted_channel()
            return res, plugin.channel, plugin._channel_id, plugin.author

    def test_hosting_invalid_host_data(self, mock_log):
        res, channel, channel_id, author = self.subject("foo")
        self.assertFalse(res, "Doesn't stop HLS resolve procedure")
        self.assertEqual(channel, "foo", "Doesn't switch channel")
        self.assertEqual(channel_id, 1, "Doesn't switch channel id")
        self.assertEqual(author, None, "Doesn't override author metadata")
        self.assertEqual(mock_log.info.mock_calls, [], "Doesn't log anything to info")
        self.assertEqual(mock_log.error.mock_calls, [], "Doesn't log anything to error")

    def test_hosting_no_host_data(self, mock_log):
        res, channel, channel_id, author = self.subject("foo", [(1, None, None, None)])
        self.assertFalse(res, "Doesn't stop HLS resolve procedure")
        self.assertEqual(channel, "foo", "Doesn't switch channel")
        self.assertEqual(channel_id, 1, "Doesn't switch channel id")
        self.assertEqual(author, None, "Doesn't override author metadata")
        self.assertEqual(mock_log.info.mock_calls, [], "Doesn't log anything to info")
        self.assertEqual(mock_log.error.mock_calls, [], "Doesn't log anything to error")

    def test_hosting_host_single(self, mock_log):
        res, channel, channel_id, author = self.subject("foo", [(1, 2, "bar", "Bar"), (2, None, None, None)])
        self.assertFalse(res, "Doesn't stop HLS resolve procedure")
        self.assertEqual(channel, "bar", "Switches channel")
        self.assertEqual(channel_id, 2, "Switches channel id")
        self.assertEqual(author, "Bar", "Overrides author metadata")
        self.assertEqual(mock_log.info.mock_calls, [
            call("foo is hosting bar"),
            call("switching to bar")
        ])
        self.assertEqual(mock_log.error.mock_calls, [], "Doesn't log anything to error")

    def test_hosting_host_single_disable(self, mock_log):
        res, channel, channel_id, author = self.subject("foo", [(1, 2, "bar", "Bar")], disable=True)
        self.assertTrue(res, "Stops HLS resolve procedure")
        self.assertEqual(channel, "foo", "Doesn't switch channel")
        self.assertEqual(channel_id, 1, "Doesn't switch channel id")
        self.assertEqual(author, None, "Doesn't override author metadata")
        self.assertEqual(mock_log.info.mock_calls, [
            call("foo is hosting bar"),
            call("hosting was disabled by command line option")
        ])
        self.assertEqual(mock_log.error.mock_calls, [], "Doesn't log anything to error")

    def test_hosting_host_multiple(self, mock_log):
        res, channel, channel_id, author = self.subject("foo", [
            (1, 2, "bar", "Bar"),
            (2, 3, "baz", "Baz"),
            (3, 4, "qux", "Qux"),
            (4, None, None, None)
        ])
        self.assertFalse(res, "Doesn't stop HLS resolve procedure")
        self.assertEqual(channel, "qux", "Switches channel")
        self.assertEqual(channel_id, 4, "Switches channel id")
        self.assertEqual(author, "Qux", "Overrides author metadata")
        self.assertEqual(mock_log.info.mock_calls, [
            call("foo is hosting bar"),
            call("switching to bar"),
            call("bar is hosting baz"),
            call("switching to baz"),
            call("baz is hosting qux"),
            call("switching to qux")
        ])
        self.assertEqual(mock_log.error.mock_calls, [], "Doesn't log anything to error")

    def test_hosting_host_multiple_loop(self, mock_log):
        res, channel, channel_id, author = self.subject("foo", [
            (1, 2, "bar", "Bar"),
            (2, 3, "baz", "Baz"),
            (3, 1, "foo", "Foo")
        ])
        self.assertTrue(res, "Stops HLS resolve procedure")
        self.assertEqual(channel, "baz", "Has switched channel")
        self.assertEqual(channel_id, 3, "Has switched channel id")
        self.assertEqual(author, "Baz", "Has overridden author metadata")
        self.assertEqual(mock_log.info.mock_calls, [
            call("foo is hosting bar"),
            call("switching to bar"),
            call("bar is hosting baz"),
            call("switching to baz"),
            call("baz is hosting foo")
        ])
        self.assertEqual(mock_log.error.mock_calls, [
            call("A loop of hosted channels has been detected, cannot find a playable stream. (foo -> bar -> baz -> foo)")
        ])


@patch("streamlink.plugins.twitch.log")
class TestTwitchReruns(unittest.TestCase):
    log_call = call("Reruns were disabled by command line option")

    def subject(self, **params):
        with patch("streamlink.plugins.twitch.TwitchAPI.stream_metadata") as mock:
            mock.return_value = None if params.pop("offline", False) else {"type": params.pop("stream_type", "live")}
            session = Streamlink()
            Twitch.bind(session, "tests.plugins.test_twitch")
            plugin = Twitch("https://www.twitch.tv/foo")
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
