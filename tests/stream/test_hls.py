import os
import unittest

import pytest
import requests_mock

from streamlink.session import Streamlink
from streamlink.stream.hls import HLSStream, HLSStreamReader
from streamlink.utils.crypto import AES, pad
from tests.mixins.stream_hls import EventedHLSStreamWriter, Playlist, Segment, Tag, TestMixinStreamHLS
from tests.mock import Mock, call, patch
from tests.resources import text


class EncryptedBase(object):
    def __init__(self, num, key, iv, *args, **kwargs):
        content = kwargs.pop("content", None)
        padding = kwargs.pop("padding", b"")
        append = kwargs.pop("append", b"")
        super(EncryptedBase, self).__init__(num, *args, **kwargs)
        aesCipher = AES.new(key, AES.MODE_CBC, iv)
        content = self.content if content is None else content
        padded = content + padding if padding else pad(content, AES.block_size, style="pkcs7")
        self.content_plain = content
        self.content = aesCipher.encrypt(padded) + append


class TagMap(Tag):
    def __init__(self, num, namespace, attrs=None):
        self.path = "map{0}".format(num)
        self.content = "[map{0}]".format(num).encode("ascii")
        d = {"URI": self.val_quoted_string(self.url(namespace))}
        d.update(attrs or {})
        super(TagMap, self).__init__("EXT-X-MAP", d)


class TagMapEnc(EncryptedBase, TagMap):
    pass


class TagKey(Tag):
    path = "encryption.key"

    def __init__(self, method="NONE", uri=None, iv=None, keyformat=None, keyformatversions=None):
        attrs = {"METHOD": method}
        if uri is not False:  # pragma: no branch
            attrs.update({"URI": lambda tag, namespace: tag.val_quoted_string(tag.url(namespace))})
        if iv is not None:  # pragma: no branch
            attrs.update({"IV": self.val_hex(iv)})
        if keyformat is not None:  # pragma: no branch
            attrs.update({"KEYFORMAT": self.val_quoted_string(keyformat)})
        if keyformatversions is not None:  # pragma: no branch
            attrs.update({"KEYFORMATVERSIONS": self.val_quoted_string(keyformatversions)})
        super(TagKey, self).__init__("EXT-X-KEY", attrs)
        self.uri = uri

    def url(self, namespace):
        return self.uri.format(namespace=namespace) if self.uri else super(TagKey, self).url(namespace)


class SegmentEnc(EncryptedBase, Segment):
    pass


class TestHLSStreamRepr(unittest.TestCase):
    def test_repr(self):
        session = Streamlink()

        stream = HLSStream(session, "https://foo.bar/playlist.m3u8")
        self.assertEqual(repr(stream), "<HLSStream ['hls', 'https://foo.bar/playlist.m3u8']>")

        stream = HLSStream(session, "https://foo.bar/playlist.m3u8", "https://foo.bar/master.m3u8")
        self.assertEqual(repr(stream), "<HLSStream ['hls', 'https://foo.bar/playlist.m3u8', 'https://foo.bar/master.m3u8']>")


class TestHLSVariantPlaylist(unittest.TestCase):
    @classmethod
    def get_master_playlist(cls, playlist):
        with text(playlist) as pl:
            return pl.read()

    def subject(self, playlist, options=None):
        with requests_mock.Mocker() as mock:
            url = "http://mocked/{0}/master.m3u8".format(self.id())
            content = self.get_master_playlist(playlist)
            mock.get(url, text=content)

            session = Streamlink(options)

            return HLSStream.parse_variant_playlist(session, url)

    def test_variant_playlist(self):
        streams = self.subject("hls/test_master.m3u8")
        assert list(streams.keys()) == ["720p", "720p_alt", "480p", "360p", "160p", "1080p (source)", "90k"]
        assert all(isinstance(stream, HLSStream) for stream in streams.values())
        assert all(stream.multivariant is not None and stream.multivariant.is_master for stream in streams.values())

        base = "http://mocked/{0}".format(self.id())
        stream = next(iter(streams.values()))
        assert repr(stream) == "<HLSStream ['hls', '{0}/720p.m3u8', '{0}/master.m3u8']>".format(base)


class EventedHLSReader(HLSStreamReader):
    __writer__ = EventedHLSStreamWriter


class EventedHLSStream(HLSStream):
    __reader__ = EventedHLSReader


@patch("streamlink.stream.hls.HLSStreamWorker.wait", Mock(return_value=True))
class TestHLSStream(TestMixinStreamHLS, unittest.TestCase):
    def get_session(self, options=None, *args, **kwargs):
        session = super(TestHLSStream, self).get_session(options)
        session.set_option("hls-live-edge", 3)

        return session

    def test_offset_and_duration(self):
        thread, segments = self.subject(
            [Playlist(1234, [Segment(0), Segment(1, duration=0.5), Segment(2, duration=0.5), Segment(3)], end=True)],
            streamoptions={"start_offset": 1, "duration": 1},
        )

        data = self.await_read(read_all=True)
        self.assertEqual(data, self.content(segments, cond=lambda s: 0 < s.num < 3), "Respects the offset and duration")
        self.assertTrue(all([self.called(s) for s in segments.values() if 0 < s.num < 3]), "Downloads second and third segment")
        self.assertFalse(any([self.called(s) for s in segments.values() if 0 > s.num > 3]), "Skips other segments")


@patch("streamlink.stream.hls.HLSStreamWorker.wait", Mock(return_value=True))
class TestHLSStreamEncrypted(TestMixinStreamHLS, unittest.TestCase):
    __stream__ = EventedHLSStream

    def get_session(self, options=None, *args, **kwargs):
        session = super(TestHLSStreamEncrypted, self).get_session(options)
        session.set_option("hls-live-edge", 3)
        session.set_option("http-headers", {"X-FOO": "BAR"})

        return session

    def gen_key(self, aes_key=None, aes_iv=None, method="AES-128", uri=None, keyformat="identity", keyformatversions=1):
        aes_key = aes_key or os.urandom(16)
        aes_iv = aes_iv or os.urandom(16)

        key = TagKey(method=method, uri=uri, iv=aes_iv, keyformat=keyformat, keyformatversions=keyformatversions)
        self.mock("GET", key.url(self.id()), content=aes_key)

        return aes_key, aes_iv, key

    @patch("streamlink.stream.hls.log")
    def test_hls_encrypted_invalid_method(self, mock_log):
        # type: (Mock)
        aesKey, aesIv, key = self.gen_key(method="INVALID")

        self.subject([
            Playlist(0, [key, SegmentEnc(1, aesKey, aesIv)], end=True)
        ])
        self.await_write()

        assert self.thread.reader.writer.closed
        assert b"".join(self.thread.data) == b""
        assert mock_log.error.mock_calls == [
            call("Failed to create decryptor: Unable to decrypt cipher INVALID")
        ]

    @patch("streamlink.stream.hls.log")
    def test_hls_encrypted_missing_uri(self, mock_log):
        # type: (Mock)
        aesKey, aesIv, key = self.gen_key(uri=False)

        self.subject([
            Playlist(0, [key, SegmentEnc(1, aesKey, aesIv)], end=True)
        ])
        self.await_write()

        assert self.thread.reader.writer.closed
        assert b"".join(self.thread.data) == b""
        assert mock_log.error.mock_calls == [
            call("Failed to create decryptor: Missing URI for decryption key")
        ]

    def test_hls_encrypted_aes128(self):
        aesKey, aesIv, key = self.gen_key()
        long = b"Test cipher block chaining mode by using a long bytes string"

        # noinspection PyTypeChecker
        thread, segments = self.subject([
            Playlist(0, [key] + [SegmentEnc(num, aesKey, aesIv) for num in range(0, 4)]),
            Playlist(4, [key] + [SegmentEnc(num, aesKey, aesIv, content=long) for num in range(4, 8)], end=True)
        ])

        self.await_write(3 + 4)
        data = self.await_read(read_all=True)
        expected = self.content(segments, prop="content_plain", cond=lambda s: s.num >= 1)
        self.assertEqual(data, expected, "Decrypts the AES-128 identity stream")
        self.assertTrue(self.called(key), "Downloads encryption key")
        self.assertEqual(self.get_mock(key).last_request._request.headers.get("X-FOO"), "BAR")
        self.assertFalse(any([self.called(s) for s in segments.values() if s.num < 1]), "Skips first segment")
        self.assertTrue(all([self.called(s) for s in segments.values() if s.num >= 1]), "Downloads all remaining segments")
        self.assertEqual(self.get_mock(segments[1]).last_request._request.headers.get("X-FOO"), "BAR")

    def test_hls_encrypted_aes128_key_uri_override(self):
        aesKey, aesIv, key = self.gen_key(uri="http://real-mocked/{namespace}/encryption.key?foo=bar")
        aesKeyInvalid = bytes([ord(aesKey[i : i + 1]) ^ 0xFF for i in range(16)])
        _, __, key_invalid = self.gen_key(aesKeyInvalid, aesIv, uri="http://mocked/{namespace}/encryption.key?foo=bar")

        # noinspection PyTypeChecker
        thread, segments = self.subject(
            [
                Playlist(0, [key_invalid] + [SegmentEnc(num, aesKey, aesIv) for num in range(0, 4)]),
                Playlist(4, [key_invalid] + [SegmentEnc(num, aesKey, aesIv) for num in range(4, 8)], end=True),
            ],
            options={"hls-segment-key-uri": "{scheme}://real-{netloc}{path}?{query}"},
        )

        self.await_write(3 + 4)
        data = self.await_read(read_all=True)
        expected = self.content(segments, prop="content_plain", cond=lambda s: s.num >= 1)
        self.assertEqual(data, expected, "Decrypts stream from custom key")
        self.assertFalse(self.called(key_invalid), "Skips encryption key")
        self.assertTrue(self.called(key), "Downloads custom encryption key")
        self.assertEqual(self.get_mock(key).last_request._request.headers.get("X-FOO"), "BAR")

    @patch("streamlink.stream.hls.log")
    def test_hls_encrypted_aes128_incorrect_block_length(self, mock_log):
        # type: (Mock)
        aesKey, aesIv, key = self.gen_key()

        thread, segments = self.subject([
            Playlist(0, [
                key,
                SegmentEnc(0, aesKey, aesIv, append=b"?"),
                SegmentEnc(1, aesKey, aesIv),
            ], end=True)
        ])
        self.await_write()
        assert self.thread.reader.writer.closed is not True

        self.await_write()
        data = self.await_read(read_all=True)
        assert data == self.content([segments[1]], prop="content_plain")
        assert mock_log.error.mock_calls == [
            call("Error while decrypting segment 0: Data must be padded to 16 byte boundary in CBC mode")
        ]

    @patch("streamlink.stream.hls.log")
    def test_hls_encrypted_aes128_incorrect_padding_length(self, mock_log):
        # type: (Mock)
        aesKey, aesIv, key = self.gen_key()

        padding = b"\x00" * (AES.block_size - len(b"[0]"))
        thread, segments = self.subject([
            Playlist(0, [
                key,
                SegmentEnc(0, aesKey, aesIv, padding=padding),
                SegmentEnc(1, aesKey, aesIv),
            ], end=True)
        ])
        self.await_write()
        assert self.thread.reader.writer.closed is not True

        self.await_write()
        data = self.await_read(read_all=True)
        assert data == self.content([segments[1]], prop="content_plain")
        assert mock_log.error.mock_calls == [call("Error while decrypting segment 0: Padding is incorrect.")]

    @patch("streamlink.stream.hls.log")
    def test_hls_encrypted_aes128_incorrect_padding_content(self, mock_log):
        # type: (Mock)
        aesKey, aesIv, key = self.gen_key()

        padding = (b"\x00" * (AES.block_size - len(b"[0]") - 1)) + b"\x10"  # bytes([AES.block_size])
        thread, segments = self.subject([
            Playlist(0, [
                key,
                SegmentEnc(0, aesKey, aesIv, padding=padding),
                SegmentEnc(1, aesKey, aesIv),
            ], end=True)
        ])
        self.await_write()
        assert self.thread.reader.writer.closed is not True

        self.await_write()
        data = self.await_read(read_all=True)
        assert data == self.content([segments[1]], prop="content_plain")
        assert mock_log.error.mock_calls == [call("Error while decrypting segment 0: PKCS#7 padding is incorrect.")]


@patch("streamlink.stream.hls.HLSStreamWorker.wait", Mock(return_value=True))
@patch("streamlink.stream.hls.HLSStreamWriter.run", Mock(return_value=True))
class TestHlsPlaylistReloadTime(TestMixinStreamHLS, unittest.TestCase):
    segments = [Segment(0, "", 11), Segment(1, "", 7), Segment(2, "", 5), Segment(3, "", 3)]

    def get_session(self, options=None, reload_time=None, *args, **kwargs):
        return super(TestHlsPlaylistReloadTime, self).get_session(
            dict(options or {}, **{"hls-live-edge": 3, "hls-playlist-reload-time": reload_time})
        )

    def subject(self, *args, **kwargs):
        thread, _ = super(TestHlsPlaylistReloadTime, self).subject(*args, **kwargs)
        self.await_read(read_all=True)

        return thread.reader.worker.playlist_reload_time

    def test_hls_playlist_reload_time_default(self):
        time = self.subject([Playlist(0, self.segments, end=True, targetduration=4)], reload_time="default")
        self.assertEqual(time, 4, "default sets the reload time to the playlist's target duration")

    def test_hls_playlist_reload_time_segment(self):
        time = self.subject([Playlist(0, self.segments, end=True, targetduration=4)], reload_time="segment")
        self.assertEqual(time, 3, "segment sets the reload time to the playlist's last segment")

    def test_hls_playlist_reload_time_segment_no_segments(self):
        time = self.subject([Playlist(0, [], end=True, targetduration=4)], reload_time="segment")
        self.assertEqual(time, 4, "segment sets the reload time to the targetduration if no segments are available")

    def test_hls_playlist_reload_time_segment_no_segments_no_targetduration(self):
        time = self.subject([Playlist(0, [], end=True, targetduration=0)], reload_time="segment")
        self.assertEqual(time, 6, "sets reload time to 6 seconds when no segments and no targetduration are available")

    def test_hls_playlist_reload_time_live_edge(self):
        time = self.subject([Playlist(0, self.segments, end=True, targetduration=4)], reload_time="live-edge")
        self.assertEqual(time, 8, "live-edge sets the reload time to the sum of the number of segments of the live-edge")

    def test_hls_playlist_reload_time_live_edge_no_segments(self):
        time = self.subject([Playlist(0, [], end=True, targetduration=4)], reload_time="live-edge")
        self.assertEqual(time, 4, "live-edge sets the reload time to the targetduration if no segments are available")

    def test_hls_playlist_reload_time_live_edge_no_segments_no_targetduration(self):
        time = self.subject([Playlist(0, [], end=True, targetduration=0)], reload_time="live-edge")
        self.assertEqual(time, 6, "sets reload time to 6 seconds when no segments and no targetduration are available")

    def test_hls_playlist_reload_time_number(self):
        time = self.subject([Playlist(0, self.segments, end=True, targetduration=4)], reload_time="2")
        self.assertEqual(time, 2, "number values override the reload time")

    def test_hls_playlist_reload_time_number_invalid(self):
        time = self.subject([Playlist(0, self.segments, end=True, targetduration=4)], reload_time="0")
        self.assertEqual(time, 4, "invalid number values set the reload time to the playlist's targetduration")

    def test_hls_playlist_reload_time_no_target_duration(self):
        time = self.subject([Playlist(0, self.segments, end=True, targetduration=0)], reload_time="default")
        self.assertEqual(time, 8, "uses the live-edge sum if the playlist is missing the targetduration data")

    def test_hls_playlist_reload_time_no_data(self):
        time = self.subject([Playlist(0, [], end=True, targetduration=0)], reload_time="default")
        self.assertEqual(time, 6, "sets reload time to 6 seconds when no data is available")


@patch("streamlink.stream.hls.FFMPEGMuxer.is_usable", Mock(return_value=True))
class TestHlsExtAudio(unittest.TestCase):
    @property
    def playlist(self):
        with text("hls/test_2.m3u8") as pl:
            return pl.read()

    def run_streamlink(self, playlist, audio_select=None):
        streamlink = Streamlink()

        if audio_select:
            streamlink.set_option("hls-audio-select", audio_select)

        master_stream = HLSStream.parse_variant_playlist(streamlink, playlist)

        return master_stream

    def test_hls_ext_audio_not_selected(self):
        master_url = "http://mocked/path/master.m3u8"

        with requests_mock.Mocker() as mock:
            mock.get(master_url, text=self.playlist)
            master_stream = self.run_streamlink(master_url)["video"]

        with pytest.raises(AttributeError):
            master_stream.substreams

        assert master_stream.url == "http://mocked/path/playlist.m3u8"

    def test_hls_ext_audio_en(self):
        """
        m3u8 with ext audio but no options should not download additional streams
        :return:
        """

        master_url = "http://mocked/path/master.m3u8"
        expected = ["http://mocked/path/playlist.m3u8", "http://mocked/path/en.m3u8"]

        with requests_mock.Mocker() as mock:
            mock.get(master_url, text=self.playlist)
            master_stream = self.run_streamlink(master_url, "en")

        substreams = master_stream["video"].substreams
        result = [x.url for x in substreams]

        # Check result
        self.assertEqual(result, expected)

    def test_hls_ext_audio_es(self):
        """
        m3u8 with ext audio but no options should not download additional streams
        :return:
        """

        master_url = "http://mocked/path/master.m3u8"
        expected = ["http://mocked/path/playlist.m3u8", "http://mocked/path/es.m3u8"]

        with requests_mock.Mocker() as mock:
            mock.get(master_url, text=self.playlist)
            master_stream = self.run_streamlink(master_url, "es")

        substreams = master_stream["video"].substreams

        result = [x.url for x in substreams]

        # Check result
        self.assertEqual(result, expected)

    def test_hls_ext_audio_all(self):
        """
        m3u8 with ext audio but no options should not download additional streams
        :return:
        """

        master_url = "http://mocked/path/master.m3u8"
        expected = ["http://mocked/path/playlist.m3u8", "http://mocked/path/en.m3u8", "http://mocked/path/es.m3u8"]

        with requests_mock.Mocker() as mock:
            mock.get(master_url, text=self.playlist)
            master_stream = self.run_streamlink(master_url, "en,es")

        substreams = master_stream["video"].substreams

        result = [x.url for x in substreams]

        # Check result
        self.assertEqual(result, expected)

    def test_hls_ext_audio_wildcard(self):
        master_url = "http://mocked/path/master.m3u8"
        expected = ["http://mocked/path/playlist.m3u8", "http://mocked/path/en.m3u8", "http://mocked/path/es.m3u8"]

        with requests_mock.Mocker() as mock:
            mock.get(master_url, text=self.playlist)
            master_stream = self.run_streamlink(master_url, "*")

        substreams = master_stream["video"].substreams

        result = [x.url for x in substreams]

        # Check result
        self.assertEqual(result, expected)
