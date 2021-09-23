import unittest
from threading import Event
from unittest.mock import MagicMock, call, patch

from streamlink.stream.hls import HLSStream, HLSStreamReader
from tests.mixins.stream_hls import EventedHLSStreamWriter, Playlist, Segment, TestMixinStreamHLS


FILTERED = "filtered"


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
        session.set_option("hls-timeout", 0)
        session.set_option("stream-timeout", 0)

        return session

    def subject(self, *args, **kwargs):
        thread, segments = super().subject(*args, **kwargs)

        return thread, thread.reader, thread.reader.writer, segments

    # don't patch should_filter_sequence here (it always returns False)
    def test_not_filtered(self):
        thread, reader, writer, segments = self.subject([
            Playlist(0, [SegmentFiltered(0), SegmentFiltered(1)], end=True)
        ])

        self.await_write(2)
        data = self.await_read()
        self.assertEqual(data, self.content(segments), "Does not filter by default")

    @patch("streamlink.stream.hls.HLSStreamWriter.should_filter_sequence", new=filter_sequence)
    @patch("streamlink.stream.hls.log")
    def test_filtered_logging(self, mock_log):
        thread, reader, writer, segments = self.subject([
            Playlist(0, [SegmentFiltered(0), SegmentFiltered(1)]),
            Playlist(2, [Segment(2), Segment(3)]),
            Playlist(4, [SegmentFiltered(4), SegmentFiltered(5)]),
            Playlist(6, [Segment(6), Segment(7)], end=True)
        ])
        data = b""

        self.assertTrue(reader.filter_event.is_set(), "Doesn't let the reader wait if not filtering")

        for i in range(2):
            self.await_write(2)
            self.assertEqual(len(mock_log.info.mock_calls), i * 2 + 1)
            self.assertEqual(mock_log.info.mock_calls[i * 2 + 0], call("Filtering out segments and pausing stream output"))
            self.assertFalse(reader.filter_event.is_set(), "Lets the reader wait if filtering")

            self.await_write(2)
            self.assertEqual(len(mock_log.info.mock_calls), i * 2 + 2)
            self.assertEqual(mock_log.info.mock_calls[i * 2 + 1], call("Resuming stream output"))
            self.assertTrue(reader.filter_event.is_set(), "Doesn't let the reader wait if not filtering")

            data += self.await_read()

        self.assertEqual(
            data,
            self.content(segments, cond=lambda s: s.num % 4 > 1),
            "Correctly filters out segments"
        )
        self.assertTrue(all([self.called(s) for s in segments.values()]), "Downloads all segments")

    @patch("streamlink.stream.hls.HLSStreamWriter.should_filter_sequence", new=filter_sequence)
    def test_filtered_timeout(self):
        thread, reader, writer, segments = self.subject([
            Playlist(0, [Segment(0), Segment(1)], end=True)
        ])

        self.await_write()
        data = self.await_read()
        self.assertEqual(data, segments[0].content, "Has read the first segment")

        # simulate a timeout by having an empty buffer
        # timeout value is set to 0
        with self.assertRaises(IOError) as cm:
            self.await_read()
        self.assertEqual(str(cm.exception), "Read timeout", "Raises a timeout error when no data is available to read")

    @patch("streamlink.stream.hls.HLSStreamWriter.should_filter_sequence", new=filter_sequence)
    def test_filtered_no_timeout(self):
        thread, reader, writer, segments = self.subject([
            Playlist(0, [SegmentFiltered(0), SegmentFiltered(1)]),
            Playlist(2, [Segment(2), Segment(3)], end=True)
        ])

        self.assertTrue(reader.filter_event.is_set(), "Doesn't let the reader wait if not filtering")

        self.await_write(2)
        self.assertFalse(reader.filter_event.is_set(), "Lets the reader wait if filtering")

        # make reader read (no data available yet)
        thread.read_wait.set()
        # once data becomes available, the reader continues reading
        self.await_write()
        self.assertTrue(reader.filter_event.is_set(), "Reader is not waiting anymore")

        thread.read_done.wait()
        thread.read_done.clear()
        self.assertFalse(thread.error, "Doesn't time out when filtering")
        self.assertEqual(b"".join(thread.data), segments[2].content, "Reads next available buffer data")

        self.await_write()
        data = self.await_read()
        self.assertEqual(data, self.content(segments, cond=lambda s: s.num >= 2))

    @patch("streamlink.stream.hls.HLSStreamWriter.should_filter_sequence", new=filter_sequence)
    def test_filtered_closed(self):
        thread, reader, writer, segments = self.subject(start=False, playlists=[
            Playlist(0, [SegmentFiltered(0), SegmentFiltered(1)], end=True)
        ])

        # mock the reader thread's filter_event.wait method, so that the main thread can wait on its call
        filter_event_wait_called = Event()
        orig_wait = reader.filter_event.wait

        def mocked_wait(*args, **kwargs):
            filter_event_wait_called.set()
            return orig_wait(*args, **kwargs)

        with patch.object(reader.filter_event, "wait", side_effect=mocked_wait):
            self.start()

            # write first filtered segment and trigger the filter_event's lock
            self.assertTrue(reader.filter_event.is_set(), "Doesn't let the reader wait if not filtering")
            self.await_write()
            self.assertFalse(reader.filter_event.is_set(), "Lets the reader wait if filtering")

            # make reader read (no data available yet)
            thread.read_wait.set()
            # before calling reader.close(), wait until reader thread's filter_event.wait was called
            if not filter_event_wait_called.wait(timeout=5):  # pragma: no cover
                raise RuntimeError("Missing filter_event.wait() call")

            # close stream while reader is waiting for filtering to end
            thread.reader.close()
            thread.read_done.wait()
            thread.read_done.clear()
            self.assertEqual(thread.data, [b""], "Stops reading on stream close")
            self.assertFalse(thread.error, "Is not a read timeout on stream close")

    def test_hls_segment_ignore_names(self):
        thread, reader, writer, segments = self.subject([
            Playlist(0, [Segment(0), Segment(1), Segment(2), Segment(3)], end=True)
        ], {"hls-segment-ignore-names": [
            ".*",
            "segment0",
            "segment2",
        ]})

        self.await_write(4)
        self.assertEqual(self.await_read(), self.content(segments, cond=lambda s: s.num % 2 > 0))
