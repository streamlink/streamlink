from datetime import datetime, timedelta
import unittest

import requests_mock

from tests.mixins.stream_hls import Playlist, Tag, Segment as _Segment, TestMixinStreamHLS
from tests.mock import MagicMock, call, patch

from streamlink import Streamlink
from streamlink.plugin import PluginError
from streamlink.plugins.twitch import Twitch, TwitchHLSStream


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
        super(TagDateRangeAd, self).__init__("EXT-X-DATERANGE", attrs)


class Segment(_Segment):
    def __init__(self, num, title="live", *args, **kwargs):
        super(Segment, self).__init__(num, title, *args, **kwargs)
        self.date = DATETIME_BASE + timedelta(seconds=num)

    def build(self, namespace):
        return "#EXT-X-PROGRAM-DATE-TIME:{0}\n{1}".format(
            self.date.strftime(DATETIME_FORMAT),
            super(Segment, self).build(namespace)
        )


class SegmentPrefetch(Segment):
    def build(self, namespace):
        return "#EXT-X-TWITCH-PREFETCH:{0}".format(self.url(namespace))


class TestPluginTwitch(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.twitch.tv/twitch',
            'https://www.twitch.tv/videos/150942279',
            'https://clips.twitch.tv/ObservantBenevolentCarabeefPhilosoraptor',
            'https://www.twitch.tv/twitch/video/292713971',
            'https://www.twitch.tv/twitch/v/292713971',
        ]
        for url in should_match:
            self.assertTrue(Twitch.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://www.twitch.tv',
        ]
        for url in should_not_match:
            self.assertFalse(Twitch.can_handle_url(url))


@patch("streamlink.stream.hls.HLSStreamWorker.wait", MagicMock(return_value=True))
class TestTwitchHLSStream(TestMixinStreamHLS, unittest.TestCase):
    __stream__ = TwitchHLSStream

    def get_session(self, options=None, disable_ads=False, low_latency=False):
        session = super(TestTwitchHLSStream, self).get_session(options)
        session.set_option("hls-live-edge", 4)
        session.set_plugin_option("twitch", "disable-ads", disable_ads)
        session.set_plugin_option("twitch", "low-latency", low_latency)

        return session

    def test_hls_disable_ads_daterange_unknown(self):
        daterange = TagDateRangeAd(start=DATETIME_BASE, duration=1, id="foo", classname="bar", custom=None)
        thread, segments = self.subject([
            Playlist(0, [daterange, Segment(0), Segment(1)], end=True)
        ], disable_ads=True, low_latency=False)

        self.assertEqual(self.await_read(read_all=True), self.content(segments), "Doesn't filter out segments")
        self.assertTrue(all(self.called(s) for s in segments.values()), "Downloads all segments")

    def test_hls_disable_ads_daterange_by_class(self):
        daterange = TagDateRangeAd(start=DATETIME_BASE, duration=1, id="foo", classname="twitch-stitched-ad", custom=None)
        thread, segments = self.subject([
            Playlist(0, [daterange, Segment(0), Segment(1)], end=True)
        ], disable_ads=True, low_latency=False)

        self.assertEqual(self.await_read(read_all=True), segments[1].content, "Filters out ad segments")
        self.assertTrue(all(self.called(s) for s in segments.values()), "Downloads all segments")

    def test_hls_disable_ads_daterange_by_id(self):
        daterange = TagDateRangeAd(start=DATETIME_BASE, duration=1, id="stitched-ad-1234", classname="/", custom=None)
        thread, segments = self.subject([
            Playlist(0, [daterange, Segment(0), Segment(1)], end=True)
        ], disable_ads=True, low_latency=False)

        self.assertEqual(self.await_read(read_all=True), segments[1].content, "Filters out ad segments")
        self.assertTrue(all(self.called(s) for s in segments.values()), "Downloads all segments")

    def test_hls_disable_ads_daterange_by_attr(self):
        daterange = TagDateRangeAd(start=DATETIME_BASE, duration=1, id="foo", classname="/", custom={"X-TV-TWITCH-AD-URL": "/"})
        thread, segments = self.subject([
            Playlist(0, [daterange, Segment(0), Segment(1)], end=True)
        ], disable_ads=True, low_latency=False)

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
class TestTwitchReruns(unittest.TestCase):
    log_call = call("Reruns were disabled by command line option")

    class StopError(Exception):
        """Stop when trying to get an access token in _get_hls_streams..."""

    @patch("streamlink.plugins.twitch.Twitch._check_for_host", return_value=None)
    @patch("streamlink.plugins.twitch.Twitch._access_token", side_effect=StopError())
    def start(self, *mocked, **params):
        with requests_mock.Mocker() as mock:
            mocked_users = mock.get(
                "https://api.twitch.tv/kraken/users?login=foo",
                json={"users": [{"_id": 1234}]}
            )
            mocked_stream = mock.get(
                "https://api.twitch.tv/kraken/streams/1234",
                json={"stream": None} if params.pop("offline", False) else {"stream": {
                    "stream_type": params.pop("stream_type", "live"),
                    "broadcast_platform": params.pop("broadcast_platform", "live"),
                    "channel": {
                        "broadcaster_software": params.pop("broadcaster_software", "")
                    }
                }}
            )

            session = Streamlink()
            Twitch.bind(session, "tests.plugins.test_twitch")
            plugin = Twitch("https://www.twitch.tv/foo")
            plugin.options.set("disable-reruns", params.pop("disable", True))
            try:
                streams = plugin.streams()
            except TestTwitchReruns.StopError:
                streams = True
                pass

            return streams, mocked_users, mocked_stream, mocked[0]

    def test_disable_reruns_live(self, mock_log):
        streams, api_users, api_stream, access_token = self.start()
        self.assertTrue(api_users.called_once)
        self.assertTrue(api_stream.called_once)
        self.assertTrue(access_token.called_once)
        self.assertTrue(streams)
        self.assertNotIn(self.log_call, mock_log.info.call_args_list)

    def test_disable_reruns_not_live(self, mock_log):
        streams, api_users, api_stream, access_token = self.start(stream_type="rerun")
        self.assertTrue(api_users.called_once)
        self.assertTrue(api_stream.called_once)
        self.assertFalse(access_token.called)
        self.assertDictEqual(streams, {})
        self.assertIn(self.log_call, mock_log.info.call_args_list)

    def test_disable_reruns_mixed(self, mock_log):
        streams, api_users, api_stream, access_token = self.start(stream_type="rerun", broadcast_platform="live")
        self.assertTrue(api_users.called_once)
        self.assertTrue(api_stream.called_once)
        self.assertFalse(access_token.called)
        self.assertDictEqual(streams, {})
        self.assertIn(self.log_call, mock_log.info.call_args_list)

    def test_disable_reruns_mixed2(self, mock_log):
        streams, api_users, api_stream, access_token = self.start(stream_type="live", broadcast_platform="rerun")
        self.assertTrue(api_users.called_once)
        self.assertTrue(api_stream.called_once)
        self.assertFalse(access_token.called)
        self.assertDictEqual(streams, {})
        self.assertIn(self.log_call, mock_log.info.call_args_list)

    def test_disable_reruns_broadcaster_software(self, mock_log):
        streams, api_users, api_stream, access_token = self.start(broadcaster_software="watch_party_rerun")
        self.assertTrue(api_users.called_once)
        self.assertTrue(api_stream.called_once)
        self.assertTrue(access_token.called_once)
        self.assertDictEqual(streams, {})
        self.assertIn(self.log_call, mock_log.info.call_args_list)

    def test_disable_reruns_offline(self, mock_log):
        streams, api_users, api_stream, access_token = self.start(offline=True)
        self.assertTrue(api_users.called_once)
        self.assertTrue(api_stream.called_once)
        self.assertTrue(access_token.called_once)
        self.assertTrue(streams)
        self.assertNotIn(self.log_call, mock_log.info.call_args_list)

    def test_enable_reruns(self, mock_log):
        streams, api_users, api_stream, access_token = self.start(disable=False)
        self.assertFalse(api_users.called)
        self.assertFalse(api_stream.called)
        self.assertTrue(access_token.called_once)
        self.assertTrue(streams)
        self.assertNotIn(self.log_call, mock_log.info.call_args_list)
