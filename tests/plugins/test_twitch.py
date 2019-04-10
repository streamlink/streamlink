import logging
import unittest
from functools import partial

from streamlink.plugins.twitch import Twitch, TwitchHLSStream

import requests_mock
from tests.mock import call, patch

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


class TestTwitchHLSStream(unittest.TestCase):
    scte35_out = "#EXT-X-DISCONTINUITY\n#EXT-X-SCTE35-OUT\n"
    scte35_out_cont = "#EXT-X-SCTE35-OUT-CONT\n"
    scte35_in = "#EXT-X-DISCONTINUITY\n#EXT-X-SCTE35-IN\n"
    segment = "#EXTINF:1.000,\nstream{0}.ts\n"

    def getMasterPlaylist(self):
        with text("hls/test_master.m3u8") as pl:
            return pl.read()

    def getPlaylist(self, media_sequence, items):
        playlist = """
#EXTM3U
#EXT-X-VERSION:5
#EXT-X-TARGETDURATION:1
#EXT-X-MEDIA-SEQUENCE:{0}
""".format(media_sequence)

        for item in items:
            if type(item) != int:
                playlist += item
            else:
                playlist += self.segment.format(item)

        return playlist

    def start_streamlink(self, kwargs=None):
        kwargs = kwargs or {}
        log.info("Executing streamlink")
        streamlink = Streamlink()

        streamlink.set_option("hls-live-edge", 4)
        streamlink.plugins.get("twitch").options.set("disable-ads", True)

        masterStream = TwitchHLSStream.parse_variant_playlist(
            streamlink,
            "http://mocked/path/master.m3u8",
            **kwargs
        )
        stream = masterStream["1080p (source)"].open()
        data = b"".join(iter(partial(stream.read, 8192), b""))
        stream.close()
        log.info("End of streamlink execution")
        return data

    def mock(self, mocked, method, url, *args, **kwargs):
        mocked[url] = method(url, *args, **kwargs)

    def get_result(self, streams, playlists):
        mocked = {}
        with requests_mock.Mocker() as mock:
            self.mock(mocked, mock.get, "http://mocked/path/master.m3u8", text=self.getMasterPlaylist())
            self.mock(mocked, mock.get, "http://mocked/path/playlist.m3u8", [{"text": p} for p in playlists])
            for i, stream in enumerate(streams):
                self.mock(mocked, mock.get, "http://mocked/path/stream{0}.ts".format(i), content=stream)
            return self.start_streamlink(), mocked

    @patch("streamlink.plugins.twitch.log")
    def test_hls_scte35_start_with_end(self, mock_logging):
        streams = ["[{0}]".format(i).encode("ascii") for i in range(12)]
        playlists = [
            self.getPlaylist(0, [self.scte35_out, 0, 1, 2, 3]),
            self.getPlaylist(4, [self.scte35_in, 4, 5, 6, 7]),
            self.getPlaylist(8, [8, 9, 10, 11]) + "#EXT-X-ENDLIST\n"
        ]
        result, mocked = self.get_result(streams, playlists)

        expected = b''.join(streams[4:12])
        self.assertEqual(expected, result)
        for i, _ in enumerate(streams):
            self.assertTrue(mocked["http://mocked/path/stream{0}.ts".format(i)].called)
        mock_logging.info.assert_has_calls([
            call("Will skip ad segments"),
            call("Will skip ads beginning with segment 0"),
            call("Will stop skipping ads beginning with segment 4")
        ])

    @patch("streamlink.plugins.twitch.log")
    def test_hls_scte35_no_start(self, mock_logging):
        streams = ["[{0}]".format(i).encode("ascii") for i in range(8)]
        playlists = [
            self.getPlaylist(0, [0, 1, 2, 3]),
            self.getPlaylist(4, [self.scte35_in, 4, 5, 6, 7]) + "#EXT-X-ENDLIST\n"
        ]
        result, mocked = self.get_result(streams, playlists)

        expected = b''.join(streams[0:8])
        self.assertEqual(expected, result)
        for i, _ in enumerate(streams):
            self.assertTrue(mocked["http://mocked/path/stream{0}.ts".format(i)].called)
        mock_logging.info.assert_has_calls([
            call("Will skip ad segments")
        ])

    @patch("streamlink.plugins.twitch.log")
    def test_hls_scte35_no_start_with_cont(self, mock_logging):
        streams = ["[{0}]".format(i).encode("ascii") for i in range(8)]
        playlists = [
            self.getPlaylist(0, [self.scte35_out_cont, 0, 1, 2, 3]),
            self.getPlaylist(4, [self.scte35_in, 4, 5, 6, 7]) + "#EXT-X-ENDLIST\n"
        ]
        result, mocked = self.get_result(streams, playlists)

        expected = b''.join(streams[4:8])
        self.assertEqual(expected, result)
        for i, _ in enumerate(streams):
            self.assertTrue(mocked["http://mocked/path/stream{0}.ts".format(i)].called)
        mock_logging.info.assert_has_calls([
            call("Will skip ad segments"),
            call("Will skip ads beginning with segment 0"),
            call("Will stop skipping ads beginning with segment 4")
        ])

    @patch("streamlink.plugins.twitch.log")
    def test_hls_scte35_no_end(self, mock_logging):
        streams = ["[{0}]".format(i).encode("ascii") for i in range(12)]
        playlists = [
            self.getPlaylist(0, [0, 1, 2, 3]),
            self.getPlaylist(4, [self.scte35_out, 4, 5, 6, 7]),
            self.getPlaylist(8, [8, 9, 10, 11]) + "#EXT-X-ENDLIST\n"
        ]
        result, mocked = self.get_result(streams, playlists)

        expected = b''.join(streams[0:4])
        self.assertEqual(expected, result)
        for i, _ in enumerate(streams):
            self.assertTrue(mocked["http://mocked/path/stream{0}.ts".format(i)].called)
        mock_logging.info.assert_has_calls([
            call("Will skip ad segments"),
            call("Will skip ads beginning with segment 4")
        ])

    @patch("streamlink.plugins.twitch.log")
    def test_hls_scte35_in_between(self, mock_logging):
        streams = ["[{0}]".format(i).encode("ascii") for i in range(20)]
        playlists = [
            self.getPlaylist(0, [0, 1, 2, 3]),
            self.getPlaylist(4, [4, 5, self.scte35_out, 6, 7]),
            self.getPlaylist(8, [8, 9, 10, 11]),
            self.getPlaylist(12, [12, 13, self.scte35_in, 14, 15]),
            self.getPlaylist(16, [16, 17, 18, 19]) + "#EXT-X-ENDLIST\n"
        ]
        result, mocked = self.get_result(streams, playlists)

        expected = b''.join(streams[0:6]) + b''.join(streams[14:20])
        self.assertEqual(expected, result)
        for i, _ in enumerate(streams):
            self.assertTrue(mocked["http://mocked/path/stream{0}.ts".format(i)].called)
        mock_logging.info.assert_has_calls([
            call("Will skip ad segments"),
            call("Will skip ads beginning with segment 6"),
            call("Will stop skipping ads beginning with segment 14")
        ])
