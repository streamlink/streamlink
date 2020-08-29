import logging
import unittest
from functools import partial

from streamlink.plugins.yotta import Yotta, YottaHLSStream

import requests_mock
from tests.mock import MagicMock, call, patch

from streamlink.session import Streamlink
from tests.resources import text


log = logging.getLogger(__name__)


class TestPluginYotta(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.yottau.com.tw/course/player/'
        ]
        for url in should_match:
            self.assertTrue(Yotta.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://yottau.com.tw',
        ]
        for url in should_not_match:
            self.assertFalse(Yotta.can_handle_url(url))


@patch("streamlink.stream.hls.HLSStreamWorker.wait", MagicMock(return_value=True))
class TestYottaHLSStream(unittest.TestCase):
    url_master = "http://mocked/path/playlist.m3u8"
    url_playlist = "http://mocked/path/1080P.m3u8"
    url_segment = "http://mocked/path/1080P{0}.ts"

    segment = "#EXTINF:1.000,\n1080P{0}.ts\n"

    def getMasterPlaylist(self):
        with text("hls/test_master.m3u8") as pl:
            return pl.read()

    def getPlaylist(self, media_sequence, items, ads=False, prefetch=None):
        playlist = """
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-ALLOW-CACHE:YES
#EXT-X-TARGETDURATION:13
#EXT-X-MEDIA-SEQUENCE:{0}
""".format(media_sequence)

        segment = self.segment
        for item in items:
            playlist += segment.format(item)

        return playlist

    def start_streamlink(self):
        log.info("Executing streamlink")
        streamlink = Streamlink()
        streamlink.set_option("hls-live-edge", 4)
        masterStream = YottaHLSStream.parse_variant_playlist(streamlink, self.url_master)
        stream = masterStream["1080p"].open()
        data = b"".join(iter(partial(stream.read, 8192), b""))
        stream.close()
        log.info("End of streamlink execution")
        return streamlink, data

    def mock(self, mocked, method, url, *args, **kwargs):
        mocked[url] = method(url, *args, **kwargs)

    def get_result(self, streams, playlists):
        mocked = {}
        with requests_mock.Mocker() as mock:
            self.mock(mocked, mock.get, self.url_master, text=self.getMasterPlaylist())
            self.mock(mocked, mock.get, self.url_playlist, [{"text": p} for p in playlists])
            for i, stream in enumerate(streams):
                self.mock(mocked, mock.get, self.url_segment.format(i), content=stream)
            streamlink, data = self.start_streamlink()
            return streamlink, data, mocked

    @patch("streamlink.plugins.yotta.log")
    def test_playlist_parse(self, mock_logging):
        streams = ["[{0}]".format(i).encode("ascii") for i in range(4)]
        playlists = [
            self.getPlaylist(0, [0, 1]),
            self.getPlaylist(2, [2, 3]) + "#EXT-X-ENDLIST\n"
        ]
        streamlink, result, mocked = self.get_result(streams, playlists)

        self.assertEqual(result, b''.join(streams[0:4]))
        for i in range(0, 4):
            self.assertTrue(mocked[self.url_segment.format(i)].called, i)
        mock_logging.info.assert_has_calls([])