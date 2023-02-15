import unittest
from threading import Event
from unittest.mock import MagicMock, call, patch

import pytest

from streamlink.stream.hls import HLSStream, HLSStreamReader
from tests.mixins.stream_hls import EventedHLSStreamWriter, Playlist, Segment, TestMixinStreamHLS


FILTERED = "filtered"
TIMEOUT_HANDSHAKE = 5


class SegmentFiltered(Segment):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = FILTERED


class _TestSubjectHLSReader(HLSStreamReader):
    __writer__ = EventedHLSStreamWriter


class _TestSubjectHLSStream(HLSStream):
    __reader__ = _TestSubjectHLSReader


@patch("streamlink.stream.hls.HLSStreamWorker.wait", MagicMock(return_value=True))
class TestFilteredHLSStream(TestMixinStreamHLS, unittest.TestCase):
    __stream__ = _TestSubjectHLSStream

    @classmethod
    def filter_sequence(cls, sequence):
        return sequence.segment.title == FILTERED

    def get_session(self, options=None, *args, **kwargs):
        session = super().get_session(options)
        session.set_option("hls-live-edge", 2)
        session.set_option("stream-timeout", 0)

        return session

    def subject(self, *args, **kwargs):
        thread, segments = super().subject(*args, **kwargs)

        return thread, thread.reader, thread.reader.writer, segments

    # don't patch should_filter_sequence here (it always returns False)
    def test_not_filtered(self):
        thread, reader, writer, segments = self.subject([
            Playlist(0, [SegmentFiltered(0), SegmentFiltered(1)], end=True),
        ])

        self.await_write(2)
        data = self.await_read()
        assert data == self.content(segments), "Does not filter by default"
        assert reader.filter_wait(timeout=0)

    @patch("streamlink.stream.hls.HLSStreamWriter.should_filter_sequence", new=filter_sequence)
    @patch("streamlink.stream.hls.log")
    def test_filtered_logging(self, mock_log):
        thread, reader, writer, segments = self.subject([
            Playlist(0, [SegmentFiltered(0), SegmentFiltered(1)]),
            Playlist(2, [Segment(2), Segment(3)]),
            Playlist(4, [SegmentFiltered(4), SegmentFiltered(5)]),
            Playlist(6, [Segment(6), Segment(7)], end=True),
        ])
        data = b""

        assert not reader.is_paused(), "Doesn't let the reader wait if not filtering"

        self.await_write(2)
        assert mock_log.info.call_args_list == [
            call("Filtering out segments and pausing stream output"),
        ]
        assert mock_log.warning.call_args_list == [], "Doesn't warn about discontinuities when filtering pre-rolls"
        assert reader.is_paused(), "Lets the reader wait if filtering"

        self.await_write(2)
        assert mock_log.info.call_args_list == [
            call("Filtering out segments and pausing stream output"),
            call("Resuming stream output"),
        ]
        assert mock_log.warning.call_args_list == [], "Doesn't warn about discontinuities when resuming after pre-rolls"
        assert not reader.is_paused(), "Doesn't let the reader wait if not filtering"

        data += self.await_read()

        self.await_write(2)
        assert mock_log.info.call_args_list == [
            call("Filtering out segments and pausing stream output"),
            call("Resuming stream output"),
            call("Filtering out segments and pausing stream output"),
        ]
        assert mock_log.warning.call_args_list == [], "Doesn't warn about discontinuities when filtering mid-rolls"
        assert reader.is_paused(), "Lets the reader wait if filtering"

        self.await_write(2)
        assert mock_log.info.call_args_list == [
            call("Filtering out segments and pausing stream output"),
            call("Resuming stream output"),
            call("Filtering out segments and pausing stream output"),
            call("Resuming stream output"),
        ]
        assert mock_log.warning.call_args_list == [
            call("Encountered a stream discontinuity. This is unsupported and will result in incoherent output data."),
        ], "Warns about discontinuities when resuming after mid-rolls"
        assert not reader.is_paused(), "Doesn't let the reader wait if not filtering"

        data += self.await_read()

        assert data == self.content(segments, cond=lambda s: s.num % 4 > 1), "Correctly filters out segments"
        assert all(self.called(s) for s in segments.values()), "Downloads all segments"

    @patch("streamlink.stream.hls.HLSStreamWriter.should_filter_sequence", new=filter_sequence)
    def test_filtered_timeout(self):
        thread, reader, writer, segments = self.subject([
            Playlist(0, [Segment(0), Segment(1)], end=True),
        ])

        self.await_write()
        data = self.await_read()
        assert data == segments[0].content, "Has read the first segment"

        # simulate a timeout by having an empty buffer
        # timeout value is set to 0
        with pytest.raises(OSError, match=r"^Read timeout$"):
            self.await_read()

    @patch("streamlink.stream.hls.HLSStreamWriter.should_filter_sequence", new=filter_sequence)
    def test_filtered_no_timeout(self):
        thread, reader, writer, segments = self.subject([
            Playlist(0, [SegmentFiltered(0), SegmentFiltered(1)]),
            Playlist(2, [Segment(2), Segment(3)], end=True),
        ])

        assert not reader.is_paused(), "Doesn't let the reader wait if not filtering"

        self.await_write(2)
        assert reader.is_paused(), "Lets the reader wait if filtering"

        # test the reader's filter_wait() method
        assert not reader.filter_wait(timeout=0), "Is filtering"

        # make reader read (no data available yet)
        thread.handshake.go()
        # once data becomes available, the reader continues reading
        self.await_write()
        assert not reader.is_paused(), "Reader is not waiting anymore"

        assert thread.handshake.wait_done(TIMEOUT_HANDSHAKE), "Doesn't time out when filtering"
        assert b"".join(thread.data) == segments[2].content, "Reads next available buffer data"

        self.await_write()
        data = self.await_read()
        assert data == self.content(segments, cond=lambda s: s.num >= 2)

    @patch("streamlink.stream.hls.HLSStreamWriter.should_filter_sequence", new=filter_sequence)
    def test_filtered_closed(self):
        thread, reader, writer, segments = self.subject(start=False, playlists=[
            Playlist(0, [SegmentFiltered(0), SegmentFiltered(1)], end=True),
        ])

        # mock the reader thread's _event_filter.wait method, so that the main thread can wait on its call
        event_filter_wait_called = Event()
        orig_wait = reader._event_filter.wait

        def mocked_wait(*args, **kwargs):
            event_filter_wait_called.set()
            return orig_wait(*args, **kwargs)

        with patch.object(reader._event_filter, "wait", side_effect=mocked_wait):
            self.start()

            # write first filtered segment and trigger the event_filter's lock
            assert not reader.is_paused(), "Doesn't let the reader wait if not filtering"
            self.await_write()
            assert reader.is_paused(), "Lets the reader wait if filtering"

            # make reader read (no data available yet)
            thread.handshake.go()
            # before calling reader.close(), wait until reader thread's event_filter.wait was called
            assert event_filter_wait_called.wait(TIMEOUT_HANDSHAKE), "Missing event_filter.wait() call"

            # close stream while reader is waiting for filtering to end
            thread.reader.close()
            assert thread.handshake.wait_done(TIMEOUT_HANDSHAKE), "Is not a read timeout on stream close"
            assert thread.data == [b""], "Stops reading on stream close"

    def test_hls_segment_ignore_names(self):
        thread, reader, writer, segments = self.subject([
            Playlist(0, [Segment(0), Segment(1), Segment(2), Segment(3)], end=True),
        ], {"hls-segment-ignore-names": [
            ".*",
            "segment0",
            "segment2",
        ]})

        self.await_write(4)
        data = self.await_read()
        assert data == self.content(segments, cond=lambda s: s.num % 2 > 0)
