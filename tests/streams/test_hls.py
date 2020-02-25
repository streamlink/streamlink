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

    def start_streamlink(self, masterPlaylist, kwargs=None):
        kwargs = kwargs or {}
        log.info("Executing streamlink")
        streamlink = Streamlink()

        # Set to default value to avoid a test fail if the default change
        streamlink.set_option("hls-live-edge", 3)

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
                                                     {'start_offset': 1, 'duration': 1})

        # Check result, each segment is 1 second, with duration=1 only one segment should be returned
        expectedResult = b''.join(streams[1:2])
        self.assertEqual(streamlinkResult, expectedResult)

    def test_hls_encryted_aes128(self):
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
