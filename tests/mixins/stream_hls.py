import unittest
from binascii import hexlify
from functools import partial
from threading import Event, Thread
from typing import List
from unittest.mock import patch

import requests_mock

from streamlink import Streamlink
from streamlink.stream.hls import HLSStream, HLSStreamWorker as _HLSStreamWorker, HLSStreamWriter as _HLSStreamWriter
from tests.testutils.handshake import Handshake


TIMEOUT_AWAIT_READ = 5
TIMEOUT_AWAIT_READ_ONCE = 5
TIMEOUT_AWAIT_WRITE = 60  # https://github.com/streamlink/streamlink/issues/3868
TIMEOUT_AWAIT_PLAYLIST_RELOAD = 5
TIMEOUT_AWAIT_PLAYLIST_WAIT = 5
TIMEOUT_AWAIT_CLOSE = 5


class HLSItemBase:
    path = ""

    def url(self, namespace):
        return "http://mocked/{namespace}/{path}".format(namespace=namespace, path=self.path)


class Playlist(HLSItemBase):
    path = "playlist.m3u8"

    def __init__(self, mediasequence=None, segments=None, end=False, targetduration=0, version=7):
        self.items = [
            Tag("EXTM3U"),
            Tag("EXT-X-VERSION", int(version)),
            Tag("EXT-X-TARGETDURATION", int(targetduration)),
        ]
        if mediasequence is not None:  # pragma: no branch
            self.items.append(Tag("EXT-X-MEDIA-SEQUENCE", int(mediasequence)))
        self.items += segments or []
        if end:
            self.items.append(Tag("EXT-X-ENDLIST"))

    def build(self, *args, **kwargs):
        return "\n".join([item.build(*args, **kwargs) for item in self.items])


class Tag(HLSItemBase):
    def __init__(self, name, attrs=None):
        self.name = name
        self.attrs = attrs

    @classmethod
    def val_quoted_string(cls, value):
        return "\"{0}\"".format(value)

    @classmethod
    def val_hex(cls, value):
        return "0x{0}".format(hexlify(value).decode("ascii"))

    def build(self, *args, **kwargs):
        attrs = None
        if type(self.attrs) == dict:
            attrs = ",".join([
                "{0}={1}".format(key, value(self, *args, **kwargs) if callable(value) else value)
                for (key, value) in self.attrs.items()
            ])
        elif self.attrs is not None:
            attrs = str(self.attrs)

        return "#{name}{attrs}".format(name=self.name, attrs=":{0}".format(attrs) if attrs else "")


class Segment(HLSItemBase):
    def __init__(self, num, title=None, duration=None, path_relative=True):
        self.num = int(num or 0)
        self.title = str(title or "")
        self.duration = float(duration or 1)
        self.path_relative = bool(path_relative)
        self.content = "[{0}]".format(self.num).encode("ascii")

    @property
    def path(self):
        return "segment{0}.ts".format(self.num)

    def build(self, namespace):
        return "#EXTINF:{duration:.3f},{title}\n{path}".format(
            duration=self.duration,
            title=self.title,
            path=self.path if self.path_relative else self.url(namespace),
        )


class EventedHLSStreamWorker(_HLSStreamWorker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.handshake_reload = Handshake()
        self.handshake_wait = Handshake()
        self.time_wait = None

    def reload_playlist(self):
        with self.handshake_reload():
            return super().reload_playlist()

    def wait(self, time):
        self.time_wait = time
        with self.handshake_wait():
            return not self.closed


class EventedHLSStreamWriter(_HLSStreamWriter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.handshake = Handshake()

    def _futures_put(self, item):
        self.futures.put_nowait(item)

    def _futures_get(self):
        return self.futures.get_nowait()

    @staticmethod
    def _future_result(future):
        return future.result(timeout=0)

    def write(self, *args, **kwargs):
        # only write once per step
        with self.handshake(Exception) as cm:
            # don't write again during teardown
            if not self.closed:
                super().write(*args, **kwargs)
        if cm.error:  # pragma: no cover
            self.reader.close()


class HLSStreamReadThread(Thread):
    """
    Run the reader on a separate thread, so that each read can be controlled from within the main thread
    """
    def __init__(self, session: Streamlink, stream: HLSStream, *args, **kwargs):
        super().__init__(*args, **kwargs, daemon=True)

        self.read_once = Event()
        self.handshake = Handshake()
        self.read_all = False
        self.data: List[bytes] = []

        self.session = session
        self.stream = stream
        self.reader = stream.__reader__(stream)

        # ensure that at least one read was attempted before closing the writer thread early
        # otherwise, the writer will close the reader's buffer, making it not block on read and yielding empty results
        def _await_read_then_close():
            self.read_once.wait(timeout=TIMEOUT_AWAIT_READ_ONCE)
            return self.writer_close()

        self.writer_close = self.reader.writer.close
        self.reader.writer.close = _await_read_then_close  # type: ignore[assignment]

    def run(self):
        while not self.reader.buffer.closed:
            # at least one read was attempted
            self.read_once.set()
            # only read once per step
            with self.handshake(OSError) as cm:
                # don't read again during teardown
                # if there is data left, close() was called manually, and it needs to be read
                if self.reader.buffer.closed and self.reader.buffer.length == 0:
                    return

                if self.read_all:
                    self.data += list(iter(partial(self.reader.read, -1), b""))
                    return

                self.data.append(self.reader.read(-1))

            if cm.error:
                return

    def reset(self):
        self.data.clear()

    def close(self):
        self.reader.close()
        self.read_once.set()
        # allow reader thread to terminate
        self.handshake.go()


class TestMixinStreamHLS(unittest.TestCase):
    __stream__ = HLSStream
    __readthread__ = HLSStreamReadThread

    session: Streamlink
    stream: HLSStream
    thread: HLSStreamReadThread

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # FIXME: fix HTTPSession.request()
        # don't sleep on mocked HTTP request failures
        self._patch_http_retry_sleep = patch("streamlink.plugin.api.http_session.time.sleep")
        self.mocker = requests_mock.Mocker()
        self.mocks = {}

    def setUp(self):
        super().setUp()

        self._patch_http_retry_sleep.start()
        self.mocker.start()

    def tearDown(self):
        super().tearDown()

        # close read thread and make sure that all threads have terminated before moving on
        self.close()
        self.await_close()

        self.mocker.stop()
        self.mocks.clear()

        self._patch_http_retry_sleep.stop()

    def mock(self, method, url, *args, **kwargs):
        self.mocks[url] = self.mocker.request(method, url, *args, **kwargs)

    def get_mock(self, item):
        return self.mocks[self.url(item)]

    def called(self, item, once=False):
        mock = self.get_mock(item)
        return mock.called_once if once else mock.called

    def url(self, item):
        return item.url(self.id())

    @staticmethod
    def content(segments, prop="content", cond=None):
        if isinstance(segments, dict):
            segments = segments.values()
        return b"".join([getattr(segment, prop) for segment in segments if cond is None or cond(segment)])

    def await_close(self, timeout=TIMEOUT_AWAIT_CLOSE):
        thread = self.thread
        thread.reader.writer.join(timeout)
        thread.reader.worker.join(timeout)
        thread.join(timeout)
        assert self.thread.reader.closed, "Stream reader is closed"

    def await_playlist_reload(self, timeout=TIMEOUT_AWAIT_PLAYLIST_RELOAD) -> None:
        worker: EventedHLSStreamWorker = self.thread.reader.worker  # type: ignore[assignment]
        assert worker.is_alive()
        assert worker.handshake_reload.step(timeout)

    def await_playlist_wait(self, timeout=TIMEOUT_AWAIT_PLAYLIST_WAIT) -> None:
        worker: EventedHLSStreamWorker = self.thread.reader.worker  # type: ignore[assignment]
        assert worker.is_alive()
        assert worker.handshake_wait.step(timeout)

    # make write calls on the write-thread and wait until it has finished
    def await_write(self, write_calls=1, timeout=TIMEOUT_AWAIT_WRITE) -> None:
        writer: EventedHLSStreamWriter = self.thread.reader.writer  # type: ignore[assignment]
        assert writer.is_alive()
        for _ in range(write_calls):
            assert writer.handshake.step(timeout)

    # make one read call on the read thread and wait until it has finished
    def await_read(self, read_all=False, timeout=TIMEOUT_AWAIT_READ):
        thread = self.thread
        thread.read_all = read_all

        assert thread.is_alive()
        assert thread.handshake.step(timeout)

        data = b"".join(thread.data)
        thread.reset()

        return data

    def get_session(self, options=None, *args, **kwargs):
        return Streamlink(options)

    # set up HLS responses, create the session and read thread and start it
    def subject(self, playlists, options=None, streamoptions=None, threadoptions=None, start=True, *args, **kwargs):
        # filter out tags and duplicate segments between playlist responses while keeping index order
        segments_all = [item for playlist in playlists for item in playlist.items if isinstance(item, Segment)]
        segments = {segment.num: segment for segment in segments_all}

        self.mock("GET", self.url(playlists[0]), [{"text": pl.build(self.id())} for pl in playlists])
        for segment in segments.values():
            self.mock("GET", self.url(segment), content=segment.content)

        self.session = self.get_session(options, *args, **kwargs)
        self.stream = self.__stream__(self.session, self.url(playlists[0]), **(streamoptions or {}))
        self.thread = self.__readthread__(self.session, self.stream, name=f"ReadThread-{self.id()}", **(threadoptions or {}))

        if start:
            self.start()

        return self.thread, segments

    def start(self):
        self.thread.reader.open()
        self.thread.start()

    def close(self):
        thread = self.thread
        thread.reader.close()
        # Allow writer and reader threads to terminate
        if isinstance(thread.reader.writer, EventedHLSStreamWriter):
            thread.reader.writer.handshake.go()
        thread.handshake.go()
