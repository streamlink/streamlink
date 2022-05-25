import unittest
from binascii import hexlify
from functools import partial
from threading import Event, Thread
from typing import List

import requests_mock

from streamlink import Streamlink
from streamlink.stream.hls import HLSStream, HLSStreamWriter as _HLSStreamWriter


TIMEOUT_AWAIT_READ = 5
TIMEOUT_AWAIT_READ_ONCE = 5
TIMEOUT_AWAIT_WRITE = 60  # https://github.com/streamlink/streamlink/issues/3868
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
            Tag("EXT-X-TARGETDURATION", int(targetduration))
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
            path=self.path if self.path_relative else self.url(namespace)
        )


class EventedHLSStreamWriter(_HLSStreamWriter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.write_wait = Event()
        self.write_done = Event()
        self.write_error = None

    def _futures_put(self, item):
        self.futures.put_nowait(item)

    def _futures_get(self):
        return self.futures.get_nowait()

    @staticmethod
    def _future_result(future):
        return future.result(timeout=0)

    def write(self, *args, **kwargs):
        # only write once per step
        self.write_wait.wait()
        self.write_wait.clear()

        try:
            # don't write again during teardown
            if not self.closed:
                super().write(*args, **kwargs)
        except Exception as err:  # pragma: no cover
            self.write_error = err
            self.reader.close()
        finally:
            # notify main thread that writing has finished
            self.write_done.set()


class HLSStreamReadThread(Thread):
    """
    Run the reader on a separate thread, so that each read can be controlled from within the main thread
    """
    def __init__(self, session: Streamlink, stream: HLSStream, *args, **kwargs):
        super().__init__(*args, **kwargs, daemon=True)

        self.read_wait = Event()
        self.read_once = Event()
        self.read_done = Event()
        self.read_all = False
        self.data: List[bytes] = []
        self.error = None

        self.session = session
        self.stream = stream
        self.reader = stream.__reader__(stream)

        # ensure that at least one read was attempted before closing the writer thread early
        # otherwise, the writer will close the reader's buffer, making it not block on read and yielding empty results
        def _await_read_then_close():
            self.read_once.wait(timeout=TIMEOUT_AWAIT_READ_ONCE)
            return self.writer_close()

        self.writer_close = self.reader.writer.close
        self.reader.writer.close = _await_read_then_close

    def run(self):
        while not self.reader.buffer.closed:
            # at least one read was attempted
            self.read_once.set()
            # only read once per step
            self.read_wait.wait()
            self.read_wait.clear()

            try:
                # don't read again during teardown
                # if there is data left, close() was called manually, and it needs to be read
                if self.reader.buffer.closed and self.reader.buffer.length == 0:
                    return

                if self.read_all:
                    self.data += list(iter(partial(self.reader.read, -1), b""))
                    return

                self.data.append(self.reader.read(-1))
            except OSError as err:
                self.error = err
                return
            finally:
                # notify main thread that reading has finished
                self.read_done.set()

    def reset(self):
        self.data[:] = []
        self.error = None

    def close(self):
        self.reader.buffer.close()
        self.read_once.set()
        self.read_wait.set()


class TestMixinStreamHLS(unittest.TestCase):
    __stream__ = HLSStream
    __readthread__ = HLSStreamReadThread

    session: Streamlink
    stream: HLSStream
    thread: HLSStreamReadThread

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mocker = requests_mock.Mocker()
        self.mocks = {}

    def setUp(self):
        super().setUp()
        self.mocker.start()

    def tearDown(self):
        super().tearDown()

        # close read thread and make sure that all threads have terminated before moving on
        self.close()
        self.await_close()

        self.mocker.stop()
        self.mocks.clear()

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

    # make write calls on the write-thread and wait until it has finished
    def await_write(self, write_calls=1, timeout=TIMEOUT_AWAIT_WRITE):
        writer = self.thread.reader.writer
        if not writer.is_alive():  # pragma: no cover
            raise RuntimeError("Write thread is not alive")

        for write_call in range(write_calls):
            writer.write_wait.set()
            done = writer.write_done.wait(timeout)
            if writer.write_error:  # pragma: no cover
                raise writer.write_error
            if not done:  # pragma: no cover
                raise RuntimeError(f"Await write timeout: write_call={write_call + 1}")
            writer.write_done.clear()

    # make one read call on the read thread and wait until it has finished
    def await_read(self, read_all=False, timeout=TIMEOUT_AWAIT_READ):
        thread = self.thread
        if not thread.is_alive():  # pragma: no cover
            raise RuntimeError("Read thread is not alive")

        thread.read_all = read_all
        thread.read_wait.set()
        done = thread.read_done.wait(timeout)

        try:
            if thread.error:  # pragma: no cover
                raise thread.error
            if not done:  # pragma: no cover
                raise RuntimeError(f"Await read timeout: read_all={read_all}")
            return b"".join(thread.data)
        finally:
            thread.read_done.clear()
            thread.reset()

    def get_session(self, options=None, *args, **kwargs):
        return Streamlink(options)

    # set up HLS responses, create the session and read thread and start it
    def subject(self, playlists, options=None, streamoptions=None, threadoptions=None, start=True, *args, **kwargs):
        # filter out tags and duplicate segments between playlist responses while keeping index order
        segments_all = [item for playlist in playlists for item in playlist.items if isinstance(item, Segment)]
        segments = dict((segment.num, segment) for segment in segments_all)

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
        if isinstance(thread.reader.writer, EventedHLSStreamWriter):
            thread.reader.writer.write_wait.set()
        thread.read_wait.set()
