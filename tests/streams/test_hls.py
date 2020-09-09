import itertools
import logging
import os
import unittest
from binascii import hexlify
from functools import partial

import pytest
import requests_mock
from Crypto.Cipher import AES
from mock import patch, Mock

from streamlink.session import Streamlink
from streamlink.stream import hls
from tests.resources import text

log = logging.getLogger(__name__)


def pkcs7_encode(data, keySize):
    val = keySize - (len(data) % keySize)
    return b''.join([data, bytes(bytearray(val * [val]))])


def encrypt(data, key, iv):
    aesCipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted_data = aesCipher.encrypt(pkcs7_encode(data, len(key)))
    return encrypted_data


@patch("streamlink.stream.hls.HLSStreamWorker.wait", Mock(return_value=True))
class TestHLS(unittest.TestCase):
    """
    Test that when invoked for the command line arguments are parsed as expected
    """
    mediaSequence = 1651

    def getMasterPlaylist(self):
        with text("hls/test_master.m3u8") as pl:
            return pl.read()

    def getPlaylist(self, aesIv, streamNameTemplate):
        playlist = """
#EXTM3U
#EXT-X-VERSION:5
#EXT-X-TARGETDURATION:1
#ID3-EQUIV-TDTG:2018-01-01T18:20:05
#EXT-X-MEDIA-SEQUENCE:{0}
#EXT-X-TWITCH-ELAPSED-SECS:3367.800
#EXT-X-TWITCH-TOTAL-SECS:3379.943
""".format(self.mediaSequence)

        playlistEnd = ""
        if aesIv is not None:
            ext_x_key = "#EXT-X-KEY:METHOD=AES-128,URI=\"{uri}\",IV=0x{iv},KEYFORMAT=identity,KEYFORMATVERSIONS=1\n"
            playlistEnd = playlistEnd + ext_x_key.format(uri="encryption_key.key", iv=hexlify(aesIv).decode("UTF-8"))

        for i in range(4):
            playlistEnd = playlistEnd + "#EXTINF:1.000,\n{0}\n".format(streamNameTemplate.format(i))
            self.mediaSequence += 1

        return playlist + playlistEnd

    def start_streamlink(self, masterPlaylist, hls_segment_key_uri=None, kwargs=None):
        kwargs = kwargs or {}
        log.info("Executing streamlink")
        streamlink = Streamlink()

        # Set to default value to avoid a test fail if the default change
        streamlink.set_option("hls-live-edge", 3)
        streamlink.set_option("hls-segment-key-uri", hls_segment_key_uri)

        masterStream = hls.HLSStream.parse_variant_playlist(streamlink, masterPlaylist, **kwargs)
        stream = masterStream["1080p (source)"].open()
        data = b"".join(iter(partial(stream.read, 8192), b""))
        stream.close()
        log.info("End of streamlink execution")
        return data

    def test_hls_non_encrypted(self):
        streams = [os.urandom(1024) for _ in range(4)]
        masterPlaylist = self.getMasterPlaylist()
        playlist = self.getPlaylist(None, "stream{0}.ts") + "#EXT-X-ENDLIST\n"
        with requests_mock.Mocker() as mock:
            mock.get("http://mocked/path/master.m3u8", text=masterPlaylist)
            mock.get("http://mocked/path/playlist.m3u8", text=playlist)
            for i, stream in enumerate(streams):
                mock.get("http://mocked/path/stream{0}.ts".format(i), content=stream)

            # Start streamlink on the generated stream
            streamlinkResult = self.start_streamlink("http://mocked/path/master.m3u8",
                                                     kwargs={'start_offset': 1, 'duration': 1})

        # Check result, each segment is 1 second, with duration=1 only one segment should be returned
        expectedResult = b''.join(streams[1:2])
        self.assertEqual(streamlinkResult, expectedResult)

    def test_hls_encrypted_aes128(self):
        # Encryption parameters
        aesKey = os.urandom(16)
        aesIv = os.urandom(16)
        # Generate stream data files
        clearStreams = [os.urandom(1024) for i in range(4)]
        encryptedStreams = [encrypt(clearStream, aesKey, aesIv) for clearStream in clearStreams]

        masterPlaylist = self.getMasterPlaylist()
        playlist1 = self.getPlaylist(aesIv, "stream{0}.ts.enc")
        playlist2 = self.getPlaylist(aesIv, "stream2_{0}.ts.enc") + "#EXT-X-ENDLIST\n"

        streamlinkResult = None
        with requests_mock.Mocker() as mock:
            mock.get("http://mocked/path/master.m3u8", text=masterPlaylist)
            mock.get("http://mocked/path/playlist.m3u8", [{'text': playlist1}, {'text': playlist2}])
            mock.get("http://mocked/path/encryption_key.key", content=aesKey)
            for i, encryptedStream in enumerate(encryptedStreams):
                mock.get("http://mocked/path/stream{0}.ts.enc".format(i), content=encryptedStream)
            for i, encryptedStream in enumerate(encryptedStreams):
                mock.get("http://mocked/path/stream2_{0}.ts.enc".format(i), content=encryptedStream)

            # Start streamlink on the generated stream
            streamlinkResult = self.start_streamlink("http://mocked/path/master.m3u8")

        # Check result
        # Live streams starts the last 3 segments from the playlist
        expectedResult = b''.join(clearStreams[1:] + clearStreams)
        self.assertEqual(streamlinkResult, expectedResult)

    def test_hls_encrypted_aes128_key_uri_override(self):
        aesKey = os.urandom(16)
        aesIv = os.urandom(16)
        aesKeyInvalid = bytes([ord(aesKey[i:i + 1]) ^ 0xFF for i in range(16)])
        clearStreams = [os.urandom(1024) for i in range(4)]
        encryptedStreams = [encrypt(clearStream, aesKey, aesIv) for clearStream in clearStreams]

        masterPlaylist = self.getMasterPlaylist()
        playlist1 = self.getPlaylist(aesIv, "stream{0}.ts.enc")
        playlist2 = self.getPlaylist(aesIv, "stream2_{0}.ts.enc") + "#EXT-X-ENDLIST\n"

        mocked_key_uri_default = None
        mocked_key_uri_override = None
        streamlinkResult = None
        with requests_mock.Mocker() as mock:
            mock.get("http://mocked/path/master.m3u8", text=masterPlaylist)
            mock.get("http://mocked/path/playlist.m3u8", [{'text': playlist1}, {'text': playlist2}])
            mocked_key_uri_default = mock.get("http://mocked/path/encryption_key.key", content=aesKeyInvalid)
            mocked_key_uri_override = mock.get("http://real-mocked/path/encryption_key.key", content=aesKey)
            for i, encryptedStream in enumerate(encryptedStreams):
                mock.get("http://mocked/path/stream{0}.ts.enc".format(i), content=encryptedStream)
            for i, encryptedStream in enumerate(encryptedStreams):
                mock.get("http://mocked/path/stream2_{0}.ts.enc".format(i), content=encryptedStream)

            streamlinkResult = self.start_streamlink(
                "http://mocked/path/master.m3u8",
                hls_segment_key_uri="{scheme}://real-{netloc}{path}{query}"
            )

        self.assertFalse(mocked_key_uri_default.called)
        self.assertTrue(mocked_key_uri_override.called)
        expectedResult = b''.join(clearStreams[1:] + clearStreams)
        self.assertEqual(streamlinkResult, expectedResult)


@patch("streamlink.stream.hls.HLSStreamWorker.wait", Mock(return_value=True))
class TestHlsPlaylistReloadTime(unittest.TestCase):
    url_playlist = "http://mocked/path/playlist.m3u8"
    url_segment = "http://mocked/path/stream{0}.ts"
    segment = "#EXTINF:{duration},\nstream{num}.ts\n"

    def getPlaylist(self, media_sequence, target_duration, offset, items):
        return (
            "#EXTM3U\n"
            "#EXT-X-VERSION:5{target_duration}\n"
            "#EXT-X-MEDIA-SEQUENCE:{media_sequence}\n"
            "{items}\n"
            "#EXT-X-ENDLIST\n"
        ).format(
            media_sequence=media_sequence,
            target_duration="\n#EXT-X-TARGETDURATION:" + str(target_duration) if target_duration else "",
            items="\n".join([self.segment.format(num=offset + i, duration=d) for i, d in enumerate(items)])
        )

    def start_streamlink(self, data, reload_time):
        streamlink = Streamlink()
        streamlink.set_option("hls-playlist-reload-time", reload_time)
        streamlink.set_option("hls-live-edge", 3)

        streams = [b"" for i in itertools.chain.from_iterable([elem[3] for elem in data])]
        playlists = [self.getPlaylist(*args) for args in data]

        with requests_mock.Mocker() as mock:
            mock.get(self.url_playlist, [{"text": p} for p in playlists])
            for i, stream in enumerate(streams):
                mock.get(self.url_segment.format(i), content=stream)

            hlsstream = hls.HLSStream(streamlink, self.url_playlist)
            reader = hlsstream.open()
            reader.close()

            return reader

    def test_hls_playlist_reload_time_default(self):
        reader = self.start_streamlink([(0, 6, 1, [11, 7, 5, 3])], "default")
        self.assertEqual(reader.worker.playlist_reload_time, 6)

    def test_hls_playlist_reload_time_segment(self):
        reader = self.start_streamlink([(0, 6, 1, [11, 7, 5, 3])], "segment")
        self.assertEqual(reader.worker.playlist_reload_time, 3)

    def test_hls_playlist_reload_time_live_edge(self):
        reader = self.start_streamlink([(0, 6, 1, [11, 7, 5, 3])], "live-edge")
        self.assertEqual(reader.worker.playlist_reload_time, 8)

    def test_hls_playlist_reload_time_number(self):
        reader = self.start_streamlink([(0, 6, 1, [11, 7, 5, 3])], "4")
        self.assertEqual(reader.worker.playlist_reload_time, 4)

    def test_hls_playlist_reload_time_number_invalid(self):
        reader = self.start_streamlink([(0, 6, 1, [11, 7, 5, 3])], "0")
        self.assertEqual(reader.worker.playlist_reload_time, 6)

    def test_hls_playlist_reload_time_no_target_duration(self):
        reader = self.start_streamlink([(0, None, 1, [11, 7, 5, 3])], "default")
        self.assertEqual(reader.worker.playlist_reload_time, 8)

    def test_hls_playlist_reload_time_no_data(self):
        reader = self.start_streamlink([(0, None, 1, [])], "default")
        self.assertEqual(reader.worker.playlist_reload_time, 15)


@patch('streamlink.stream.hls.FFMPEGMuxer.is_usable', Mock(return_value=True))
class TestHlsExtAudio(unittest.TestCase):
    @property
    def playlist(self):
        with text("hls/test_2.m3u8") as pl:
            return pl.read()

    def run_streamlink(self, playlist, audio_select=None):
        streamlink = Streamlink()

        if audio_select:
            streamlink.set_option("hls-audio-select", audio_select)

        master_stream = hls.HLSStream.parse_variant_playlist(streamlink, playlist)

        return master_stream

    def test_hls_ext_audio_not_selected(self):
        master_url = "http://mocked/path/master.m3u8"

        with requests_mock.Mocker() as mock:
            mock.get(master_url, text=self.playlist)
            master_stream = self.run_streamlink(master_url)['video']

        with pytest.raises(AttributeError):
            master_stream.substreams

        assert master_stream.url == 'http://mocked/path/playlist.m3u8'

    def test_hls_ext_audio_en(self):
        """
        m3u8 with ext audio but no options should not download additional streams
        :return:
        """

        master_url = "http://mocked/path/master.m3u8"
        expected = ['http://mocked/path/playlist.m3u8', 'http://mocked/path/en.m3u8']

        with requests_mock.Mocker() as mock:
            mock.get(master_url, text=self.playlist)
            master_stream = self.run_streamlink(master_url, 'en')

        substreams = master_stream['video'].substreams
        result = [x.url for x in substreams]

        # Check result
        self.assertEqual(result, expected)

    def test_hls_ext_audio_es(self):
        """
        m3u8 with ext audio but no options should not download additional streams
        :return:
        """

        master_url = "http://mocked/path/master.m3u8"
        expected = ['http://mocked/path/playlist.m3u8', 'http://mocked/path/es.m3u8']

        with requests_mock.Mocker() as mock:
            mock.get(master_url, text=self.playlist)
            master_stream = self.run_streamlink(master_url, 'es')

        substreams = master_stream['video'].substreams

        result = [x.url for x in substreams]

        # Check result
        self.assertEqual(result, expected)

    def test_hls_ext_audio_all(self):
        """
        m3u8 with ext audio but no options should not download additional streams
        :return:
        """

        master_url = "http://mocked/path/master.m3u8"
        expected = ['http://mocked/path/playlist.m3u8', 'http://mocked/path/en.m3u8', 'http://mocked/path/es.m3u8']

        with requests_mock.Mocker() as mock:
            mock.get(master_url, text=self.playlist)
            master_stream = self.run_streamlink(master_url, 'en,es')

        substreams = master_stream['video'].substreams

        result = [x.url for x in substreams]

        # Check result
        self.assertEqual(result, expected)

    def test_hls_ext_audio_wildcard(self):
        master_url = "http://mocked/path/master.m3u8"
        expected = ['http://mocked/path/playlist.m3u8', 'http://mocked/path/en.m3u8', 'http://mocked/path/es.m3u8']

        with requests_mock.Mocker() as mock:
            mock.get(master_url, text=self.playlist)
            master_stream = self.run_streamlink(master_url, '*')

        substreams = master_stream['video'].substreams

        result = [x.url for x in substreams]

        # Check result
        self.assertEqual(result, expected)
