from __future__ import annotations

import itertools
import os
import unittest
from datetime import datetime, timedelta, timezone
from threading import Event
from typing import NamedTuple
from unittest.mock import Mock, call, patch

import freezegun
import pytest
import requests_mock as rm
from requests.exceptions import InvalidSchema

from streamlink.session import Streamlink
from streamlink.stream.hls import (
    M3U8,
    HLSPlaylist,
    HLSSegment,
    HLSStream,
    HLSStreamReader,
    M3U8Parser,
    MuxedHLSStream,
)
from streamlink.stream.hls.hls import log
from streamlink.utils.crypto import AES, pad
from tests.mixins.stream_hls import EventedHLSStreamWorker, EventedHLSStreamWriter, Playlist, Segment, Tag, TestMixinStreamHLS
from tests.resources import text


EPOCH = datetime(2000, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc)
ONE_SECOND = timedelta(seconds=1.0)


class EncryptedBase:
    content: bytes
    content_plain: bytes

    def __init__(self, num, key, iv, *args, content=None, padding=b"", append=b"", **kwargs):
        super().__init__(num, *args, **kwargs)
        aesCipher = AES.new(key, AES.MODE_CBC, iv)
        content = self.content if content is None else content
        padded = content + padding if padding else pad(content, AES.block_size, style="pkcs7")
        self.content_plain = content
        self.content = aesCipher.encrypt(padded) + append


class TagMap(Tag):
    def __init__(self, num, namespace, attrs=None):
        self.path = f"map{num}"
        self.content = f"[map{num}]".encode("ascii")
        super().__init__(
            "EXT-X-MAP",
            {
                "URI": self.val_quoted_string(self.url(namespace)),
                **(attrs or {}),
            },
        )


class TagMapEnc(EncryptedBase, TagMap):
    pass


class TagKey(Tag):
    _id = itertools.count()

    def __init__(self, method="NONE", uri=None, iv=None, keyformat=None, keyformatversions=None):
        attrs = {"METHOD": method}
        if uri is not False:  # pragma: no branch
            attrs["URI"] = lambda tag, namespace: tag.val_quoted_string(tag.url(namespace))
        if iv is not None:  # pragma: no branch
            attrs["IV"] = self.val_hex(iv)
        if keyformat is not None:  # pragma: no branch
            attrs["KEYFORMAT"] = self.val_quoted_string(keyformat)
        if keyformatversions is not None:  # pragma: no branch
            attrs["KEYFORMATVERSIONS"] = self.val_quoted_string(keyformatversions)
        super().__init__("EXT-X-KEY", attrs)
        self.uri = uri
        self.path = f"encryption{next(self._id)}.key"

    def url(self, namespace):
        return self.uri.format(namespace=namespace) if self.uri else super().url(namespace)


class SegmentEnc(EncryptedBase, Segment):
    pass


def test_logger_name():
    assert log.name == "streamlink.stream.hls"


def test_repr(session: Streamlink):
    stream = HLSStream(session, "https://foo.bar/playlist.m3u8")
    assert repr(stream) == "<HLSStream ['hls', 'https://foo.bar/playlist.m3u8']>"

    stream = HLSStream(session, "https://foo.bar/playlist.m3u8", "https://foo.bar/master.m3u8")
    assert repr(stream) == "<HLSStream ['hls', 'https://foo.bar/playlist.m3u8', 'https://foo.bar/master.m3u8']>"


class TestHLSVariantPlaylist:
    @pytest.fixture()
    def streams(self, request: pytest.FixtureRequest, requests_mock: rm.Mocker, session: Streamlink):
        url = f"http://mocked/{request.node.originalname}/master.m3u8"
        playlist = getattr(request, "param", "")

        with text(playlist) as fd:
            content = fd.read()
        requests_mock.get(url, text=content)

        return HLSStream.parse_variant_playlist(session, url)

    @pytest.mark.parametrize("streams", ["hls/test_master.m3u8"], indirect=True)
    def test_variant_playlist(self, request: pytest.FixtureRequest, streams: dict[str, HLSStream]):
        assert list(streams.keys()) == ["720p", "720p_alt", "480p", "360p", "160p", "1080p (source)", "90k"]
        assert all(isinstance(stream, HLSStream) for stream in streams.values())
        assert all(stream.multivariant is not None and stream.multivariant.is_master for stream in streams.values())

        base = f"http://mocked/{request.node.originalname}"
        stream = next(iter(streams.values()))
        assert repr(stream) == f"<HLSStream ['hls', '{base}/720p.m3u8', '{base}/master.m3u8']>"

        assert stream.multivariant is not None
        assert stream.multivariant.uri == f"{base}/master.m3u8"
        assert stream.url_master == f"{base}/master.m3u8"

    def test_url_master(self, session: Streamlink):
        stream = HLSStream(session, "http://mocked/foo", url_master="http://mocked/master.m3u8")

        assert stream.multivariant is None
        assert stream.url == "http://mocked/foo"
        assert stream.url_master == "http://mocked/master.m3u8"


class EventedWorkerHLSStreamReader(HLSStreamReader):
    __worker__ = EventedHLSStreamWorker


class EventedWriterHLSStreamReader(HLSStreamReader):
    __writer__ = EventedHLSStreamWriter


class EventedWorkerHLSStream(HLSStream):
    __reader__ = EventedWorkerHLSStreamReader


class EventedWriterHLSStream(HLSStream):
    __reader__ = EventedWriterHLSStreamReader


@patch("streamlink.stream.hls.hls.HLSStreamWorker.wait", Mock(return_value=True))
class TestHLSStream(TestMixinStreamHLS, unittest.TestCase):
    def get_session(self, options=None, *args, **kwargs):
        session = super().get_session(options)
        session.set_option("hls-live-edge", 3)

        return session

    def test_playlist_end(self):
        segments = self.subject([
            Playlist(0, [Segment(0)], end=True),
        ])

        assert self.await_read(read_all=True) == self.content(segments), "Stream ends and read-all handshake doesn't time out"

    def test_playlist_end_on_empty_reload(self):
        segments = self.subject([
            Playlist(0, [Segment(0)]),
            Playlist(0, [Segment(0)], end=True),
        ])

        assert self.await_read(read_all=True) == self.content(segments), "Stream ends and read-all handshake doesn't time out"

    def test_offset_and_duration(self):
        segments = self.subject(
            [
                Playlist(1234, [Segment(0), Segment(1, duration=0.5), Segment(2, duration=0.5), Segment(3)], end=True),
            ],
            streamoptions={"start_offset": 1, "duration": 1},
        )

        data = self.await_read(read_all=True)
        assert data == self.content(segments, cond=lambda s: 0 < s.num < 3), "Respects the offset and duration"
        assert all(self.called(s) for s in segments.values() if 0 < s.num < 3), "Downloads second and third segment"
        assert not any(self.called(s) for s in segments.values() if 0 > s.num > 3), "Skips other segments"

    def test_map(self):
        discontinuity = Tag("EXT-X-DISCONTINUITY")
        map1 = TagMap(1, self.id())
        map2 = TagMap(2, self.id())
        self.mock("GET", self.url(map1), content=map1.content)
        self.mock("GET", self.url(map2), content=map2.content)

        segments = self.subject(
            [
                Playlist(0, [map1, Segment(0), Segment(1), Segment(2), Segment(3)]),
                Playlist(4, [map1, Segment(4), map2, Segment(5), Segment(6), discontinuity, map1, Segment(7)], end=True),
            ],
            options={"stream-segment-threads": 2},
        )

        data = self.await_read(read_all=True, timeout=None)
        assert data == self.content([
            map1, segments[1], segments[2], segments[3],
            segments[4], map2, segments[5], segments[6], map1, segments[7],
        ])  # fmt: skip
        assert self.called(map1, once=True), "Downloads first map only once"
        assert self.called(map2, once=True), "Downloads second map only once"


# TODO: finally rewrite the segmented/HLS test setup using pytest and replace redundant setups with parametrization
@patch("streamlink.stream.hls.hls.HLSStreamWorker.wait", Mock(return_value=True))
class TestHLSStreamPlaylistReloadDiscontinuity(TestMixinStreamHLS, unittest.TestCase):
    @patch("streamlink.stream.hls.hls.log")
    def test_no_discontinuity(self, mock_log: Mock):
        segments = self.subject([
            Playlist(0, [Segment(0), Segment(1)]),
            Playlist(2, [Segment(2), Segment(3)]),
            Playlist(4, [Segment(4), Segment(5)], end=True),
        ])

        data = self.await_read(read_all=True)
        assert data == self.content(segments)
        assert all(self.called(s) for s in segments.values())
        assert mock_log.warning.call_args_list == []

    @patch("streamlink.stream.hls.hls.log")
    def test_discontinuity_single_segment(self, mock_log: Mock):
        segments = self.subject([
            Playlist(0, [Segment(0), Segment(1)]),
            Playlist(2, [Segment(2), Segment(3)]),
            Playlist(5, [Segment(5), Segment(6)]),
            Playlist(8, [Segment(8), Segment(9)], end=True),
        ])

        data = self.await_read(read_all=True)
        assert data == self.content(segments)
        assert all(self.called(s) for s in segments.values())
        assert mock_log.warning.call_args_list == [
            call("Skipped segment 4 after playlist reload. This is unsupported and will result in incoherent output data."),
            call("Skipped segment 7 after playlist reload. This is unsupported and will result in incoherent output data."),
        ]

    @patch("streamlink.stream.hls.hls.log")
    def test_discontinuity_multiple_segments(self, mock_log: Mock):
        segments = self.subject([
            Playlist(0, [Segment(0), Segment(1)]),
            Playlist(2, [Segment(2), Segment(3)]),
            Playlist(6, [Segment(6), Segment(7)]),
            Playlist(10, [Segment(10), Segment(11)], end=True),
        ])

        data = self.await_read(read_all=True)
        assert data == self.content(segments)
        assert all(self.called(s) for s in segments.values())
        assert mock_log.warning.call_args_list == [
            call("Skipped segments 4-5 after playlist reload. This is unsupported and will result in incoherent output data."),
            call("Skipped segments 8-9 after playlist reload. This is unsupported and will result in incoherent output data."),
        ]


class TestHLSStreamWorker(TestMixinStreamHLS, unittest.TestCase):
    __stream__ = EventedWorkerHLSStream

    OPTIONS = {"stream-timeout": 1}

    def tearDown(self) -> None:
        worker: EventedHLSStreamWorker = self.thread.reader.worker  # type: ignore[assignment]
        # don't await the handshakes on error
        worker.handshake_wait.go()
        worker.handshake_reload.go()
        return super().tearDown()

    def get_session(self, options=None, *args, **kwargs):
        return super().get_session({**self.OPTIONS, **(options or {})}, *args, **kwargs)

    def test_segment_queue_timing_threshold_reached(self) -> None:
        self.subject(
            start=False,
            playlists=[
                Playlist(0, targetduration=5, segments=[Segment(0)]),
                # no EXT-X-ENDLIST, last mocked playlist response will be repreated forever
                Playlist(0, targetduration=5, segments=[Segment(0), Segment(1)]),
            ],
        )
        worker: EventedHLSStreamWorker = self.thread.reader.worker  # type: ignore[assignment]
        targetduration = ONE_SECOND * 5

        with (
            freezegun.freeze_time(EPOCH) as frozen_time,
            patch("streamlink.stream.hls.hls.log") as mock_log,
        ):
            self.start()

            assert worker.handshake_reload.wait_ready(1), "Loads playlist for the first time"
            assert worker.playlist_sequence == -1, "Initial sequence number"
            assert worker.playlist_sequence_last == EPOCH, "Sets the initial last queue time"

            # first playlist reload has taken one second
            frozen_time.tick(ONE_SECOND)
            self.await_playlist_reload(1)

            assert worker.handshake_wait.wait_ready(1), "Arrives at wait() call #1"
            assert worker.playlist_sequence == 1, "Updates the sequence number"
            assert worker.playlist_sequence_last == EPOCH + ONE_SECOND, "Updates the last queue time"
            assert worker.playlist_targetduration == 5.0

            # trigger next reload when the target duration has passed
            frozen_time.tick(targetduration)
            self.await_playlist_wait(1)
            self.await_playlist_reload(1)

            assert worker.handshake_wait.wait_ready(1), "Arrives at wait() call #2"
            assert worker.playlist_sequence == 2, "Updates the sequence number again"
            assert worker.playlist_sequence_last == EPOCH + ONE_SECOND + targetduration, "Updates the last queue time again"
            assert worker.playlist_targetduration == 5.0

            for num in range(3, 6):
                # trigger next reload when the target duration has passed
                frozen_time.tick(targetduration)
                self.await_playlist_wait(1)
                self.await_playlist_reload(1)

                assert worker.handshake_wait.wait_ready(1), f"Arrives at wait() call #{num}"
                assert worker.playlist_sequence == 2, "Sequence number is unchanged"
                assert worker.playlist_sequence_last == EPOCH + ONE_SECOND + targetduration, "Last queue time is unchanged"
                assert worker.playlist_targetduration == 5.0

            assert mock_log.warning.call_args_list == []

            # trigger next reload when the target duration has passed
            frozen_time.tick(targetduration)
            self.await_playlist_wait(1)
            self.await_playlist_reload(1)

            self.await_read(read_all=True)
            self.await_close(1)

            assert mock_log.warning.call_args_list == [call("No new segments in playlist for more than 15.00s. Stopping...")]

    def test_segment_queue_timing_threshold_reached_ignored(self) -> None:
        segments = self.subject(
            start=False,
            options={"hls-segment-queue-threshold": 0},
            playlists=[
                # no EXT-X-ENDLIST, last mocked playlist response will be repreated forever
                Playlist(0, targetduration=5, segments=[Segment(0)]),
            ],
        )
        worker: EventedHLSStreamWorker = self.thread.reader.worker  # type: ignore[assignment]
        targetduration = ONE_SECOND * 5

        with freezegun.freeze_time(EPOCH) as frozen_time:
            self.start()

            assert worker.handshake_reload.wait_ready(1), "Loads playlist for the first time"
            assert worker.playlist_sequence == -1, "Initial sequence number"
            assert worker.playlist_sequence_last == EPOCH, "Sets the initial last queue time"

            # first playlist reload has taken one second
            frozen_time.tick(ONE_SECOND)
            self.await_playlist_reload(1)

            assert worker.handshake_wait.wait_ready(1), "Arrives at first wait() call"
            assert worker.playlist_sequence == 1, "Updates the sequence number"
            assert worker.playlist_sequence_last == EPOCH + ONE_SECOND, "Updates the last queue time"
            assert worker.playlist_targetduration == 5.0
            assert self.await_read() == self.content(segments)

            # keep reloading a couple of times
            for num in range(10):
                frozen_time.tick(targetduration)
                self.await_playlist_wait(1)
                self.await_playlist_reload(1)

                assert worker.handshake_wait.wait_ready(1), f"Arrives at wait() #{num + 1}"
                assert worker.playlist_sequence == 1, "Sequence number is unchanged"
                assert worker.playlist_sequence_last == EPOCH + ONE_SECOND, "Last queue time is unchanged"

        assert self.thread.data == [], "No new data"
        assert worker.is_alive()

        # make stream end gracefully to avoid any unnecessary thread blocking
        self.thread.reader.writer.put(None)

    def test_segment_queue_timing_threshold_reached_min(self) -> None:
        self.subject(
            start=False,
            playlists=[
                # no EXT-X-ENDLIST, last mocked playlist response will be repreated forever
                Playlist(0, targetduration=1, segments=[Segment(0)]),
            ],
        )
        worker: EventedHLSStreamWorker = self.thread.reader.worker  # type: ignore[assignment]
        targetduration = ONE_SECOND

        with (
            freezegun.freeze_time(EPOCH) as frozen_time,
            patch("streamlink.stream.hls.hls.log") as mock_log,
        ):
            self.start()

            assert worker.handshake_reload.wait_ready(1), "Loads playlist for the first time"
            assert worker.playlist_sequence == -1, "Initial sequence number"
            assert worker.playlist_sequence_last == EPOCH, "Sets the initial last queue time"

            # first playlist reload has taken one second
            frozen_time.tick(ONE_SECOND)
            self.await_playlist_reload(1)

            assert worker.handshake_wait.wait_ready(1), "Arrives at wait() call #1"
            assert worker.playlist_sequence == 1, "Updates the sequence number"
            assert worker.playlist_sequence_last == EPOCH + ONE_SECOND, "Updates the last queue time"
            assert worker.playlist_targetduration == 1.0

            for num in range(2, 7):
                # trigger next reload when the target duration has passed
                frozen_time.tick(targetduration)
                self.await_playlist_wait(1)
                self.await_playlist_reload(1)

                assert worker.handshake_wait.wait_ready(1), f"Arrives at wait() call #{num}"
                assert worker.playlist_sequence == 1, "Sequence number is unchanged"
                assert worker.playlist_sequence_last == EPOCH + ONE_SECOND, "Last queue time is unchanged"
                assert worker.playlist_targetduration == 1.0

            assert mock_log.warning.call_args_list == []

            # trigger next reload when the target duration has passed
            frozen_time.tick(targetduration)
            self.await_playlist_wait(1)
            self.await_playlist_reload(1)

            assert mock_log.warning.call_args_list == [call("No new segments in playlist for more than 5.00s. Stopping...")]

    def test_playlist_reload_offset(self) -> None:
        segments = self.subject(
            start=False,
            playlists=[
                Playlist(0, targetduration=5, segments=[Segment(0)]),
                Playlist(1, targetduration=5, segments=[Segment(1)]),
                Playlist(2, targetduration=5, segments=[Segment(2)]),
                Playlist(3, targetduration=5, segments=[Segment(3)]),
                Playlist(4, targetduration=5, segments=[Segment(4)], end=True),
            ],
        )
        worker: EventedHLSStreamWorker = self.thread.reader.worker  # type: ignore[assignment]
        targetduration = ONE_SECOND * 5

        with freezegun.freeze_time(EPOCH) as frozen_time:
            self.start()

            assert worker.handshake_reload.wait_ready(1), "Arrives at initial playlist reload"
            assert worker.playlist_reload_last == EPOCH, "Sets the initial value of the last reload time"

            # adjust clock and reload playlist: let it take one second
            frozen_time.move_to(worker.playlist_reload_last + ONE_SECOND)
            self.await_playlist_reload()
            assert worker.playlist_reload_time == 5.0, "Uses the playlist's targetduration as reload time"

            # time_completed = 00:00:01; time_elapsed = 1s
            assert worker.handshake_wait.wait_ready(1), "Arrives at first wait() call"
            assert worker.playlist_sequence == 1, "Has queued first segment"
            assert worker.playlist_end is None, "Stream hasn't ended yet"
            assert worker.time_wait == 4.0, "Waits for 4 seconds out of the 5 seconds reload time"
            self.await_playlist_wait()

            assert worker.handshake_reload.wait_ready(1), "Arrives at second playlist reload"
            assert worker.playlist_reload_last == EPOCH + targetduration, \
                "Last reload time is the sum of reload+wait time (=targetduration)"  # fmt: skip

            # adjust clock and reload playlist: let it exceed targetduration by two seconds
            frozen_time.move_to(worker.playlist_reload_last + targetduration + ONE_SECOND * 2)
            self.await_playlist_reload()
            assert worker.playlist_reload_time == 5.0, "Uses the playlist's targetduration as reload time"

            # time_completed = 00:00:12; time_elapsed = 7s (exceeded 5s targetduration)
            assert worker.handshake_wait.wait_ready(1), "Arrives at second wait() call"
            assert worker.playlist_sequence == 2, "Has queued second segment"
            assert worker.playlist_end is None, "Stream hasn't ended yet"
            assert worker.time_wait == 0.0, "Doesn't wait when reloading took too long"
            self.await_playlist_wait()

            assert worker.handshake_reload.wait_ready(1), "Arrives at third playlist reload"
            assert worker.playlist_reload_last == EPOCH + targetduration * 2 + ONE_SECOND * 2, \
                "Sets last reload time to current time when reloading took too long (changes the interval)"  # fmt: skip

            # adjust clock and reload playlist: let it take one second again
            frozen_time.move_to(worker.playlist_reload_last + ONE_SECOND)
            self.await_playlist_reload()
            assert worker.playlist_reload_time == 5.0, "Uses the playlist's targetduration as reload time"

            # time_completed = 00:00:13; time_elapsed = 1s
            assert worker.handshake_wait.wait_ready(1), "Arrives at third wait() call"
            assert worker.playlist_sequence == 3, "Has queued third segment"
            assert worker.playlist_end is None, "Stream hasn't ended yet"
            assert worker.time_wait == 4.0, "Waits for 4 seconds out of the 5 seconds reload time"
            self.await_playlist_wait()

            assert worker.handshake_reload.wait_ready(1), "Arrives at fourth playlist reload"
            assert worker.playlist_reload_last == EPOCH + targetduration * 3 + ONE_SECOND * 2, \
                "Last reload time is the sum of reload+wait time (=targetduration) of the changed interval"  # fmt: skip

            # adjust clock and reload playlist: simulate no fetch+processing delay
            frozen_time.move_to(worker.playlist_reload_last)
            self.await_playlist_reload()
            assert worker.playlist_reload_time == 5.0, "Uses the playlist's targetduration as reload time"

            # time_completed = 00:00:17; time_elapsed = 0s
            assert worker.handshake_wait.wait_ready(1), "Arrives at fourth wait() call"
            assert worker.playlist_sequence == 4, "Has queued fourth segment"
            assert worker.playlist_end is None, "Stream hasn't ended yet"
            assert worker.time_wait == 5.0, "Waits for the whole reload time"
            self.await_playlist_wait()

            assert worker.handshake_reload.wait_ready(1), "Arrives at fifth playlist reload"
            assert worker.playlist_reload_last == EPOCH + targetduration * 4 + ONE_SECOND * 2, \
                "Last reload time is the sum of reload+wait time (no delay)"  # fmt: skip

            # adjusting the clock is not needed anymore
            self.await_playlist_reload()
            assert self.await_read(read_all=True) == self.content(segments)
            self.await_close()
            assert worker.playlist_end == 4, "Stream has ended"
            assert not worker.handshake_wait.wait_ready(0), "Doesn't wait once ended"
            assert not worker.handshake_reload.wait_ready(0), "Doesn't reload playlist once ended"


@patch("streamlink.stream.hls.hls.HLSStreamWorker.wait", Mock(return_value=True))
class TestHLSStreamByterange(TestMixinStreamHLS, unittest.TestCase):
    __stream__ = EventedWriterHLSStream

    # The dummy segments in the error tests are required because the writer's run loop would otherwise continue forever
    # due to the segment's future result being None (no requests result), and we can't await the end of the stream
    # without waiting for the stream's timeout error. The dummy segments ensure that we can call await_write for these
    # successful segments, so we can close the stream afterward and safely make the test assertions.
    # The EventedHLSStreamWriter could also implement await_fetch, but this is unnecessarily more complex than it already is.

    @patch("streamlink.stream.hls.hls.log")
    def test_unknown_offset(self, mock_log: Mock):
        self.subject([
            Playlist(
                0,
                [
                    Tag("EXT-X-BYTERANGE", "3"),
                    Segment(0),
                    Segment(1),
                ],
                end=True,
            ),
        ])

        self.await_write(2 - 1)
        self.thread.close()

        assert mock_log.error.call_args_list == [
            call("Failed to fetch segment 0: Missing BYTERANGE offset"),
        ]
        assert not self.called(Segment(0))

    @patch("streamlink.stream.hls.hls.log")
    def test_unknown_offset_map(self, mock_log: Mock):
        map1 = TagMap(1, self.id(), {"BYTERANGE": '"1234"'})
        self.mock("GET", self.url(map1), content=map1.content)
        self.subject([
            Playlist(
                0,
                [
                    Segment(0),
                    map1,
                    Segment(1),
                ],
                end=True,
            ),
        ])

        self.await_write(3 - 1)
        self.thread.close()

        assert mock_log.error.call_args_list == [
            call("Failed to fetch map for segment 1: Missing BYTERANGE offset"),
        ]
        assert not self.called(map1)

    @patch("streamlink.stream.hls.hls.log")
    def test_invalid_offset_reference(self, mock_log: Mock):
        self.subject([
            Playlist(
                0,
                [
                    Tag("EXT-X-BYTERANGE", "3@0"),
                    Segment(0),
                    Segment(1),
                    Tag("EXT-X-BYTERANGE", "5"),
                    Segment(2),
                    Segment(3),
                ],
                end=True,
            ),
        ])

        self.await_write(4 - 1)
        self.thread.close()

        assert mock_log.error.call_args_list == [
            call("Failed to fetch segment 2: Missing BYTERANGE offset"),
        ]
        assert self.mocks[self.url(Segment(0))].last_request._request.headers["Range"] == "bytes=0-2"
        assert not self.called(Segment(2))

    def test_offsets(self):
        map1 = TagMap(1, self.id(), {"BYTERANGE": '"1234@0"'})
        map2 = TagMap(2, self.id(), {"BYTERANGE": '"42@1337"'})
        self.mock("GET", self.url(map1), content=map1.content)
        self.mock("GET", self.url(map2), content=map2.content)
        s1, s2, s3, s4, s5 = Segment(0), Segment(1), Segment(2), Segment(3), Segment(4)

        self.subject([
            Playlist(
                0,
                [
                    map1,
                    Tag("EXT-X-BYTERANGE", "5@3"),
                    s1,
                    Tag("EXT-X-BYTERANGE", "7"),
                    s2,
                    map2,
                    Tag("EXT-X-BYTERANGE", "11"),
                    s3,
                    Tag("EXT-X-BYTERANGE", "17@13"),
                    s4,
                    Tag("EXT-X-BYTERANGE", "19"),
                    s5,
                ],
                end=True,
            ),
        ])

        self.await_write(1 + 2 + 1 + 3)  # 1 map, 2 partial segments, 1 map, 3 partial segments
        self.await_read(read_all=True)
        assert self.mocks[self.url(map1)].last_request._request.headers["Range"] == "bytes=0-1233"
        assert self.mocks[self.url(map2)].last_request._request.headers["Range"] == "bytes=1337-1378"
        assert self.mocks[self.url(s1)].last_request._request.headers["Range"] == "bytes=3-7"
        assert self.mocks[self.url(s2)].last_request._request.headers["Range"] == "bytes=8-14"
        assert self.mocks[self.url(s3)].last_request._request.headers["Range"] == "bytes=15-25"
        assert self.mocks[self.url(s4)].last_request._request.headers["Range"] == "bytes=13-29"
        assert self.mocks[self.url(s5)].last_request._request.headers["Range"] == "bytes=30-48"


@patch("streamlink.stream.hls.hls.HLSStreamWorker.wait", Mock(return_value=True))
class TestHLSStreamEncrypted(TestMixinStreamHLS, unittest.TestCase):
    __stream__ = EventedWriterHLSStream

    def get_session(self, options=None, *args, **kwargs):
        session = super().get_session(options)
        session.set_option("hls-live-edge", 3)
        session.set_option("http-headers", {"X-FOO": "BAR"})

        return session

    def gen_key(
        self,
        aes_key=None,
        aes_iv=None,
        method="AES-128",
        uri=None,
        keyformat="identity",
        keyformatversions=1,
        mock=None,
    ):
        aes_key = aes_key or os.urandom(16)
        aes_iv = aes_iv or os.urandom(16)

        key = TagKey(method=method, uri=uri, iv=aes_iv, keyformat=keyformat, keyformatversions=keyformatversions)
        self.mock("GET", key.url(self.id()), **(mock if mock else {"content": aes_key}))

        return aes_key, aes_iv, key

    @patch("streamlink.stream.hls.hls.log")
    def test_hls_encrypted_invalid_method(self, mock_log: Mock):
        aesKey, aesIv, key = self.gen_key(method="INVALID")

        self.subject([
            Playlist(0, [key, SegmentEnc(1, aesKey, aesIv)], end=True),
        ])
        self.await_write()

        self.thread.close()
        self.await_close()

        assert b"".join(self.thread.data) == b""
        assert mock_log.error.mock_calls == [
            call("Failed to create decryptor: Unable to decrypt cipher INVALID"),
        ]

    @patch("streamlink.stream.hls.hls.log")
    def test_hls_encrypted_missing_uri(self, mock_log: Mock):
        aesKey, aesIv, key = self.gen_key(uri=False)

        self.subject([
            Playlist(0, [key, SegmentEnc(1, aesKey, aesIv)], end=True),
        ])
        self.await_write()

        self.thread.close()
        self.await_close()

        assert b"".join(self.thread.data) == b""
        assert mock_log.error.mock_calls == [
            call("Failed to create decryptor: Missing URI for decryption key"),
        ]

    @patch("streamlink.stream.hls.hls.log")
    def test_hls_encrypted_missing_adapter(self, mock_log: Mock):
        aesKey, aesIv, key = self.gen_key(uri="foo://bar/baz", mock={"exc": InvalidSchema})

        self.subject([
            Playlist(0, [key, SegmentEnc(1, aesKey, aesIv)], end=True),
        ])
        self.await_write()

        self.thread.close()
        self.await_close()

        assert b"".join(self.thread.data) == b""
        assert mock_log.error.mock_calls == [
            call("Failed to create decryptor: Unable to find connection adapter for key URI: foo://bar/baz"),
        ]

    def test_hls_encrypted_aes128(self):
        aesKey, aesIv, key = self.gen_key()
        long = b"Test cipher block chaining mode by using a long bytes string"

        # noinspection PyTypeChecker
        segments = self.subject([
            Playlist(0, [key] + [SegmentEnc(num, aesKey, aesIv) for num in range(4)]),
            Playlist(4, [key] + [SegmentEnc(num, aesKey, aesIv, content=long) for num in range(4, 8)], end=True),
        ])

        self.await_write(3 + 4)
        data = self.await_read(read_all=True)
        self.await_close()

        expected = self.content(segments, prop="content_plain", cond=lambda s: s.num >= 1)
        assert data == expected, "Decrypts the AES-128 identity stream"
        assert self.called(key, once=True), "Downloads encryption key only once"
        assert self.get_mock(key).last_request._request.headers.get("X-FOO") == "BAR"
        assert not any(self.called(s) for s in segments.values() if s.num < 1), "Skips first segment"
        assert all(self.called(s) for s in segments.values() if s.num >= 1), "Downloads all remaining segments"
        assert self.get_mock(segments[1]).last_request._request.headers.get("X-FOO") == "BAR"

    def test_hls_encrypted_aes128_with_map(self):
        aesKey, aesIv, key = self.gen_key()
        map1 = TagMapEnc(1, namespace=self.id(), key=aesKey, iv=aesIv)
        map2 = TagMapEnc(2, namespace=self.id(), key=aesKey, iv=aesIv)
        self.mock("GET", self.url(map1), content=map1.content)
        self.mock("GET", self.url(map2), content=map2.content)

        segments = self.subject([
            Playlist(0, [key, map1] + [SegmentEnc(num, aesKey, aesIv) for num in range(2)]),
            Playlist(2, [key, map2] + [SegmentEnc(num, aesKey, aesIv) for num in range(2, 4)], end=True),
        ])

        self.await_write(1 + 2 + 1 + 2)  # 1 map, 2 segments, 1 map, 2 segments
        data = self.await_read(read_all=True)
        self.await_close()

        assert data == self.content(
            [
                map1,
                segments[0],
                segments[1],
                map2,
                segments[2],
                segments[3],
            ],
            prop="content_plain",
        )

    def test_hls_encrypted_aes128_with_differently_encrypted_map(self):
        aesKey1, aesIv1, key1 = self.gen_key()  # init key
        aesKey2, aesIv2, key2 = self.gen_key()  # media key
        map1 = TagMapEnc(1, namespace=self.id(), key=aesKey1, iv=aesIv1)
        map2 = TagMapEnc(2, namespace=self.id(), key=aesKey1, iv=aesIv1)
        self.mock("GET", self.url(map1), content=map1.content)
        self.mock("GET", self.url(map2), content=map2.content)

        segments = self.subject([
            Playlist(0, [key1, map1, key2] + [SegmentEnc(num, aesKey2, aesIv2) for num in range(2)]),
            Playlist(2, [key1, map2, key2] + [SegmentEnc(num, aesKey2, aesIv2) for num in range(2, 4)], end=True),
        ])

        self.await_write(1 + 2 + 1 + 2)  # 1 map, 2 segments, 1 map, 2 segments
        data = self.await_read(read_all=True)
        self.await_close()

        assert data == self.content(
            [
                map1,
                segments[0],
                segments[1],
                map2,
                segments[2],
                segments[3],
            ],
            prop="content_plain",
        )

    def test_hls_encrypted_aes128_with_plaintext_map(self):
        aesKey, aesIv, key = self.gen_key()
        map1 = TagMap(1, namespace=self.id())
        map2 = TagMap(2, namespace=self.id())
        self.mock("GET", self.url(map1), content=map1.content)
        self.mock("GET", self.url(map2), content=map2.content)

        segments = self.subject([
            Playlist(0, [map1, key] + [SegmentEnc(num, aesKey, aesIv) for num in range(2)]),
            Playlist(2, [map2, key] + [SegmentEnc(num, aesKey, aesIv) for num in range(2, 4)], end=True),
        ])

        self.await_write(1 + 2 + 1 + 2)  # 1 map, 2 segments, 1 map, 2 segments
        data = self.await_read(read_all=True)
        self.await_close()

        assert data == (
            map1.content
            + segments[0].content_plain
            + segments[1].content_plain
            + map2.content
            + segments[2].content_plain
            + segments[3].content_plain
        )

    def test_hls_encrypted_aes128_key_uri_override(self):
        aesKey, aesIv, key = self.gen_key(uri="http://real-mocked/{namespace}/encryption.key?foo=bar")
        aesKeyInvalid = bytes(ord(aesKey[i : i + 1]) ^ 0xFF for i in range(16))
        _, __, key_invalid = self.gen_key(aesKeyInvalid, aesIv, uri="http://mocked/{namespace}/encryption.key?foo=bar")

        # noinspection PyTypeChecker
        segments = self.subject(
            [
                Playlist(0, [key_invalid] + [SegmentEnc(num, aesKey, aesIv) for num in range(4)]),
                Playlist(4, [key_invalid] + [SegmentEnc(num, aesKey, aesIv) for num in range(4, 8)], end=True),
            ],
            options={"hls-segment-key-uri": "{scheme}://real-{netloc}{path}?{query}"},
        )

        self.await_write(3 + 4)
        data = self.await_read(read_all=True)
        self.await_close()

        expected = self.content(segments, prop="content_plain", cond=lambda s: s.num >= 1)
        assert data == expected, "Decrypts stream from custom key"
        assert not self.called(key_invalid), "Skips encryption key"
        assert self.called(key, once=True), "Downloads custom encryption key"
        assert self.get_mock(key).last_request._request.headers.get("X-FOO") == "BAR"

    @patch("streamlink.stream.hls.hls.log")
    def test_hls_encrypted_aes128_incorrect_block_length(self, mock_log: Mock):
        aesKey, aesIv, key = self.gen_key()

        segments = self.subject([
            Playlist(
                0,
                [
                    key,
                    SegmentEnc(0, aesKey, aesIv, append=b"?"),
                    SegmentEnc(1, aesKey, aesIv),
                ],
                end=True,
            ),
        ])
        self.await_write()
        assert self.thread.reader.writer.is_alive()

        self.await_write()
        data = self.await_read(read_all=True)
        self.await_close()

        assert data == self.content([segments[1]], prop="content_plain")
        assert mock_log.error.mock_calls == [
            call("Error while decrypting segment 0: Data must be padded to 16 byte boundary in CBC mode"),
        ]

    @patch("streamlink.stream.hls.hls.log")
    def test_hls_encrypted_aes128_incorrect_padding_length(self, mock_log: Mock):
        aesKey, aesIv, key = self.gen_key()

        padding = b"\x00" * (AES.block_size - len(b"[0]"))
        segments = self.subject([
            Playlist(
                0,
                [
                    key,
                    SegmentEnc(0, aesKey, aesIv, padding=padding),
                    SegmentEnc(1, aesKey, aesIv),
                ],
                end=True,
            ),
        ])
        self.await_write()
        assert self.thread.reader.writer.is_alive()

        self.await_write()
        data = self.await_read(read_all=True)
        self.await_close()

        assert data == self.content([segments[1]], prop="content_plain")
        assert mock_log.error.mock_calls == [call("Error while decrypting segment 0: Padding is incorrect.")]

    @patch("streamlink.stream.hls.hls.log")
    def test_hls_encrypted_aes128_incorrect_padding_content(self, mock_log: Mock):
        aesKey, aesIv, key = self.gen_key()

        padding = (b"\x00" * (AES.block_size - len(b"[0]") - 1)) + bytes([AES.block_size])
        segments = self.subject([
            Playlist(
                0,
                [
                    key,
                    SegmentEnc(0, aesKey, aesIv, padding=padding),
                    SegmentEnc(1, aesKey, aesIv),
                ],
                end=True,
            ),
        ])
        self.await_write()
        assert self.thread.reader.writer.is_alive()

        self.await_write()
        data = self.await_read(read_all=True)
        self.await_close()

        assert data == self.content([segments[1]], prop="content_plain")
        assert mock_log.error.mock_calls == [call("Error while decrypting segment 0: PKCS#7 padding is incorrect.")]


@patch("streamlink.stream.hls.hls.HLSStreamWorker.wait", Mock(return_value=True))
class TestHlsPlaylistReloadTime(TestMixinStreamHLS, unittest.TestCase):
    segments = [
        Segment(0, duration=11),
        Segment(1, duration=7),
        Segment(2, duration=5),
        Segment(3, duration=3),
    ]

    def get_session(self, options=None, reload_time=None, *args, **kwargs):
        return super().get_session(
            dict(
                options or {},
                **{
                    "hls-live-edge": 3,
                    "hls-playlist-reload-time": reload_time,
                },
            ),
        )

    def subject(self, *args, **kwargs):
        super().subject(*args, start=False, **kwargs)

        # mock the worker thread's _playlist_reload_time method, so that the main thread can wait on its call
        playlist_reload_time_called = Event()
        orig_playlist_reload_time = self.thread.reader.worker._playlist_reload_time

        def mocked_playlist_reload_time(*args, **kwargs):
            playlist_reload_time_called.set()
            return orig_playlist_reload_time(*args, **kwargs)

        # immediately kill the writer thread as we don't need it and don't want to wait for its queue polling to end
        def mocked_queue_get():
            return None

        with (
            patch.object(self.thread.reader.worker, "_playlist_reload_time", side_effect=mocked_playlist_reload_time),
            patch.object(self.thread.reader.writer, "_queue_get", side_effect=mocked_queue_get),
        ):
            self.start()

            if not playlist_reload_time_called.wait(timeout=5):  # pragma: no cover
                raise RuntimeError("Missing _playlist_reload_time() call")

            # wait for the worker thread to terminate, so that deterministic assertions can be done about the reload time
            self.thread.reader.worker.join()

            return self.thread.reader.worker.playlist_reload_time

    def test_hls_playlist_reload_time_default(self):
        time = self.subject([Playlist(0, self.segments, end=True, targetduration=4)], reload_time="default")
        assert time == 4, "default sets the reload time to the playlist's target duration"

    def test_hls_playlist_reload_time_segment(self):
        time = self.subject([Playlist(0, self.segments, end=True, targetduration=4)], reload_time="segment")
        assert time == 3, "segment sets the reload time to the playlist's last segment"

    def test_hls_playlist_reload_time_segment_no_segments(self):
        time = self.subject([Playlist(0, [], end=True, targetduration=4)], reload_time="segment")
        assert time == 4, "segment sets the reload time to the targetduration if no segments are available"

    def test_hls_playlist_reload_time_segment_no_segments_no_targetduration(self):
        time = self.subject([Playlist(0, [], end=True, targetduration=0)], reload_time="segment")
        assert time == 6, "sets reload time to 6 seconds when no segments and no targetduration are available"

    def test_hls_playlist_reload_time_live_edge(self):
        time = self.subject([Playlist(0, self.segments, end=True, targetduration=4)], reload_time="live-edge")
        assert time == 8, "live-edge sets the reload time to the sum of the number of segments of the live-edge"

    def test_hls_playlist_reload_time_live_edge_no_segments(self):
        time = self.subject([Playlist(0, [], end=True, targetduration=4)], reload_time="live-edge")
        assert time == 4, "live-edge sets the reload time to the targetduration if no segments are available"

    def test_hls_playlist_reload_time_live_edge_no_segments_no_targetduration(self):
        time = self.subject([Playlist(0, [], end=True, targetduration=0)], reload_time="live-edge")
        assert time == 6, "sets reload time to 6 seconds when no segments and no targetduration are available"

    def test_hls_playlist_reload_time_number(self):
        time = self.subject([Playlist(0, self.segments, end=True, targetduration=4)], reload_time="2")
        assert time == 2, "number values override the reload time"

    def test_hls_playlist_reload_time_number_invalid(self):
        time = self.subject([Playlist(0, self.segments, end=True, targetduration=4)], reload_time="0")
        assert time == 4, "invalid number values set the reload time to the playlist's targetduration"

    def test_hls_playlist_reload_time_no_target_duration(self):
        time = self.subject([Playlist(0, self.segments, end=True, targetduration=0)], reload_time="default")
        assert time == 8, "uses the live-edge sum if the playlist is missing the targetduration data"

    def test_hls_playlist_reload_time_no_data(self):
        time = self.subject([Playlist(0, [], end=True, targetduration=0)], reload_time="default")
        assert time == 6, "sets reload time to 6 seconds when no data is available"


@patch("streamlink.stream.hls.hls.log")
@patch("streamlink.stream.hls.hls.HLSStreamWorker.wait", Mock(return_value=True))
@patch("streamlink.stream.hls.hls.HLSStreamWorker._segment_queue_timing_threshold_reached", Mock(return_value=False))
class TestHlsPlaylistParseErrors(TestMixinStreamHLS, unittest.TestCase):
    __stream__ = EventedWriterHLSStream

    class FakePlaylist(NamedTuple):
        is_master: bool = False
        iframes_only: bool = False

    class InvalidPlaylist(Playlist):
        def build(self, *args, **kwargs):
            return "invalid"

    def test_generic(self, mock_log):
        self.subject([self.InvalidPlaylist()])
        assert self.await_read(read_all=True) == b""
        self.await_close()
        assert self.thread.reader.buffer.closed, "Closes the stream on initial playlist parsing error"
        assert mock_log.debug.mock_calls == [call("Reloading playlist")]
        assert mock_log.error.mock_calls == [call("Missing #EXTM3U header")]

    def test_reload(self, mock_log):
        segments = self.subject([
            Playlist(1, [Segment(0)]),
            self.InvalidPlaylist(),
            self.InvalidPlaylist(),
            Playlist(2, [Segment(2)], end=True),
        ])
        self.await_write(2)
        data = self.await_read(read_all=True)
        assert data == self.content(segments)
        self.close()
        self.await_close()
        assert mock_log.warning.mock_calls == [
            call("Failed to reload playlist: Missing #EXTM3U header"),
            call("Failed to reload playlist: Missing #EXTM3U header"),
        ]

    @patch("streamlink.stream.hls.hls.parse_m3u8", Mock(return_value=FakePlaylist(is_master=True)))
    def test_is_master(self, mock_log):
        self.subject([Playlist()])
        assert self.await_read(read_all=True) == b""
        self.await_close()
        assert self.thread.reader.buffer.closed, "Closes the stream on initial playlist parsing error"
        assert mock_log.debug.mock_calls == [call("Reloading playlist")]
        assert mock_log.error.mock_calls == [
            call(f"Attempted to play a variant playlist, use 'hls://{self.stream.url}' instead"),
        ]

    @patch("streamlink.stream.hls.hls.parse_m3u8", Mock(return_value=FakePlaylist(iframes_only=True)))
    def test_iframes_only(self, mock_log):
        self.subject([Playlist()])
        assert self.await_read(read_all=True) == b""
        self.await_close()
        assert self.thread.reader.buffer.closed, "Closes the stream on initial playlist parsing error"
        assert mock_log.debug.mock_calls == [call("Reloading playlist")]
        assert mock_log.error.mock_calls == [call("Streams containing I-frames only are not playable")]


class TestHlsExtAudio:
    @pytest.fixture(autouse=True)
    def _is_usable(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("streamlink.stream.hls.hls.FFMPEGMuxer.is_usable", Mock(return_value=True))

    @pytest.fixture(autouse=True)
    def _playlist(self, requests_mock: rm.Mocker):
        with text("hls/test_2.m3u8") as playlist:
            requests_mock.get("http://mocked/path/master.m3u8", text=playlist.read())
            yield

    @pytest.fixture()
    def stream(self, session: Streamlink):
        streams = HLSStream.parse_variant_playlist(session, "http://mocked/path/master.m3u8")
        assert "video" in streams

        return streams["video"]

    def test_no_selection(self, stream: HLSStream):
        assert not isinstance(stream, MuxedHLSStream)
        assert stream.url == "http://mocked/path/playlist.m3u8"

    @pytest.mark.parametrize(
        ("session", "selection"),
        [
            pytest.param({"hls-audio-select": ["en"]}, "http://mocked/path/en.m3u8", id="English"),
            pytest.param({"hls-audio-select": ["es"]}, "http://mocked/path/es.m3u8", id="Spanish"),
        ],
        indirect=["session"],
    )
    def test_selection(self, session: Streamlink, stream: MuxedHLSStream, selection: str):
        assert isinstance(stream, MuxedHLSStream)
        assert [substream.url for substream in stream.substreams] == [
            "http://mocked/path/playlist.m3u8",
            selection,
        ]

    @pytest.mark.parametrize(
        "session",
        [
            pytest.param({"hls-audio-select": ["*"]}, id="wildcard"),
            pytest.param({"hls-audio-select": ["en", "es"]}, id="multiple locales"),
        ],
        indirect=["session"],
    )
    def test_multiple(self, session: Streamlink, stream: MuxedHLSStream):
        assert isinstance(stream, MuxedHLSStream)
        assert [substream.url for substream in stream.substreams] == [
            "http://mocked/path/playlist.m3u8",
            "http://mocked/path/en.m3u8",
            "http://mocked/path/es.m3u8",
        ]


class TestM3U8ParserLogging:
    @pytest.mark.parametrize(("loglevel", "has_logs"), [("trace", False), ("all", True)])
    def test_log(self, caplog: pytest.LogCaptureFixture, loglevel: str, has_logs: bool):
        caplog.set_level(loglevel, "streamlink")

        parser = M3U8Parser[M3U8, HLSSegment, HLSPlaylist]()
        with text("hls/test_1.m3u8") as pl:
            data = pl.read()
        parser.parse(data)

        assert bool(caplog.records) is has_logs
