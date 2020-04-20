import logging
import unittest
from functools import partial

from streamlink.plugins.twitch import Twitch, TwitchHLSStream

import requests_mock
from tests.mock import MagicMock, call, patch

from streamlink.session import Streamlink
from tests.resources import text


log = logging.getLogger(__name__)


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
class TestTwitchHLSStream(unittest.TestCase):
    url_master = "http://mocked/path/master.m3u8"
    url_playlist = "http://mocked/path/playlist.m3u8"
    url_segment = "http://mocked/path/stream{0}.ts"

    segment = "#EXTINF:1.000,\nstream{0}.ts\n"
    segment_ad = "#EXTINF:1.000,Amazon|123456789\nstream{0}.ts\n"
    prefetch = "#EXT-X-TWITCH-PREFETCH:{0}\n"

    def getMasterPlaylist(self):
        with text("hls/test_master.m3u8") as pl:
            return pl.read()

    def getPlaylist(self, media_sequence, items, ads=False, prefetch=None):
        playlist = """
#EXTM3U
#EXT-X-VERSION:5
#EXT-X-TARGETDURATION:1
#EXT-X-MEDIA-SEQUENCE:{0}
""".format(media_sequence)

        segment = self.segment if not ads else self.segment_ad
        for item in items:
            playlist += segment.format(item)
        for item in prefetch or []:
            playlist += self.prefetch.format(self.url_segment.format(item))

        return playlist

    def start_streamlink(self, disable_ads=False, low_latency=False, kwargs=None):
        kwargs = kwargs or {}
        log.info("Executing streamlink")
        streamlink = Streamlink()

        streamlink.set_option("hls-live-edge", 4)
        streamlink.set_plugin_option("twitch", "disable-ads", disable_ads)
        streamlink.set_plugin_option("twitch", "low-latency", low_latency)

        masterStream = TwitchHLSStream.parse_variant_playlist(streamlink, self.url_master, **kwargs)
        stream = masterStream["1080p (source)"].open()
        data = b"".join(iter(partial(stream.read, 8192), b""))
        stream.close()
        log.info("End of streamlink execution")
        return streamlink, data

    def mock(self, mocked, method, url, *args, **kwargs):
        mocked[url] = method(url, *args, **kwargs)

    def get_result(self, streams, playlists, **kwargs):
        mocked = {}
        with requests_mock.Mocker() as mock:
            self.mock(mocked, mock.get, self.url_master, text=self.getMasterPlaylist())
            self.mock(mocked, mock.get, self.url_playlist, [{"text": p} for p in playlists])
            for i, stream in enumerate(streams):
                self.mock(mocked, mock.get, self.url_segment.format(i), content=stream)
            streamlink, data = self.start_streamlink(**kwargs)
            return streamlink, data, mocked

    @patch("streamlink.plugins.twitch.log")
    def test_hls_disable_ads_preroll(self, mock_logging):
        streams = ["[{0}]".format(i).encode("ascii") for i in range(6)]
        playlists = [
            self.getPlaylist(0, [0, 1], ads=True),
            self.getPlaylist(2, [2, 3], ads=True),
            self.getPlaylist(4, [4, 5]) + "#EXT-X-ENDLIST\n"
        ]
        streamlink, result, mocked = self.get_result(streams, playlists, disable_ads=True)

        self.assertEqual(result, b''.join(streams[4:6]))
        for i in range(0, 6):
            self.assertTrue(mocked[self.url_segment.format(i)].called, i)
        mock_logging.info.assert_has_calls([
            call("Will skip ad segments"),
            call("Waiting for pre-roll ads to finish, be patient")
        ])
        self.assertEqual(mock_logging.info.call_count, 2)

    @patch("streamlink.plugins.twitch.log")
    def test_hls_disable_ads_no_preroll(self, mock_logging):
        streams = ["[{0}]".format(i).encode("ascii") for i in range(6)]
        playlists = [
            self.getPlaylist(0, [0, 1]),
            self.getPlaylist(2, [2, 3], ads=True),
            self.getPlaylist(4, [4, 5]) + "#EXT-X-ENDLIST\n"
        ]
        streamlink, result, mocked = self.get_result(streams, playlists, disable_ads=True)

        self.assertEqual(result, b''.join(streams[0:2]) + b''.join(streams[4:6]))
        for i in range(0, 6):
            self.assertTrue(mocked[self.url_segment.format(i)].called, i)
        mock_logging.info.assert_has_calls([
            call("Will skip ad segments")
        ])

    @patch("streamlink.plugins.twitch.log")
    def test_hls_no_disable_ads(self, mock_logging):
        streams = ["[{0}]".format(i).encode("ascii") for i in range(4)]
        playlists = [
            self.getPlaylist(0, [0, 1], ads=True),
            self.getPlaylist(2, [2, 3]) + "#EXT-X-ENDLIST\n"
        ]
        streamlink, result, mocked = self.get_result(streams, playlists, disable_ads=False)

        self.assertEqual(result, b''.join(streams[0:4]))
        for i in range(0, 4):
            self.assertTrue(mocked[self.url_segment.format(i)].called, i)
        mock_logging.info.assert_has_calls([])

    @patch("streamlink.plugins.twitch.log")
    def test_hls_prefetch(self, mock_logging):
        streams = ["[{0}]".format(i).encode("ascii") for i in range(10)]
        playlists = [
            self.getPlaylist(0, [0, 1, 2, 3], prefetch=[4, 5]),
            self.getPlaylist(4, [4, 5, 6, 7], prefetch=[8, 9]) + "#EXT-X-ENDLIST\n"
        ]
        streamlink, result, mocked = self.get_result(streams, playlists, low_latency=True)

        self.assertEqual(2, streamlink.options.get("hls-live-edge"))
        self.assertEqual(True, streamlink.options.get("hls-segment-stream-data"))

        expected = b''.join(streams[4:10])
        self.assertEqual(expected, result)
        for i in range(0, 3):
            self.assertFalse(mocked[self.url_segment.format(i)].called, i)
        for i in range(4, 9):
            self.assertTrue(mocked[self.url_segment.format(i)].called, i)
        mock_logging.info.assert_has_calls([
            call("Low latency streaming (HLS live edge: 2)")
        ])

    @patch("streamlink.plugins.twitch.log")
    def test_hls_prefetch_no_low_latency(self, mock_logging):
        streams = ["[{0}]".format(i).encode("ascii") for i in range(10)]
        playlists = [
            self.getPlaylist(0, [0, 1, 2, 3], prefetch=[4, 5]),
            self.getPlaylist(4, [4, 5, 6, 7], prefetch=[8, 9]) + "#EXT-X-ENDLIST\n"
        ]
        streamlink, result, mocked = self.get_result(streams, playlists)

        self.assertEqual(4, streamlink.options.get("hls-live-edge"))
        self.assertEqual(False, streamlink.options.get("hls-segment-stream-data"))

        expected = b''.join(streams[0:8])
        self.assertEqual(expected, result)
        for i in range(0, 7):
            self.assertTrue(mocked[self.url_segment.format(i)].called, i)
        for i in range(8, 9):
            self.assertFalse(mocked[self.url_segment.format(i)].called, i)
        mock_logging.info.assert_has_calls([])

    @patch("streamlink.plugins.twitch.log")
    def test_hls_no_low_latency_no_prefetch(self, mock_logging):
        streams = ["[{0}]".format(i).encode("ascii") for i in range(10)]
        playlists = [
            self.getPlaylist(0, [0, 1, 2, 3], prefetch=[]),
            self.getPlaylist(4, [4, 5, 6, 7], prefetch=[]) + "#EXT-X-ENDLIST\n"
        ]
        streamlink, result, mocked = self.get_result(streams, playlists, low_latency=True)

        self.assertTrue(streamlink.get_plugin_option("twitch", "low-latency"))
        self.assertFalse(streamlink.get_plugin_option("twitch", "disable-ads"))

        mock_logging.info.assert_has_calls([
            call("Low latency streaming (HLS live edge: 2)"),
            call("This is not a low latency stream")
        ])


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
                "https://api.twitch.tv/kraken/users.json?login=foo",
                json={"users": [{"_id": 1234}]}
            )
            mocked_stream = mock.get(
                "https://api.twitch.tv/kraken/streams/1234.json",
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
