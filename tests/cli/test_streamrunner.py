from __future__ import annotations

import errno
from collections import deque
from collections.abc import Callable
from pathlib import Path
from threading import Thread
from unittest.mock import Mock, patch

import pytest

from streamlink.stream.stream import StreamIO
from streamlink_cli.console.progress import Progress
from streamlink_cli.output import FileOutput, HTTPOutput, PlayerOutput
from streamlink_cli.streamrunner import PlayerPollThread, StreamRunner, log as streamrunnerlogger
from tests.testutils.handshake import Handshake


TIMEOUT_AWAIT_HANDSHAKE = 1
TIMEOUT_AWAIT_THREADJOIN = 1


class _TestableWithHandshake:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.handshake = Handshake()


class EventedPlayerPollThread(_TestableWithHandshake, PlayerPollThread):
    POLLING_INTERVAL = 0

    def poll(self):
        with self.handshake():
            return super().poll()

    def close(self):
        super().close()
        # Let thread terminate on close()
        self.handshake.go()


class FakeStream(_TestableWithHandshake, StreamIO):
    """Fake stream implementation, for feeding sample data to the stream runner and simulating read pauses and read errors"""

    def __init__(self) -> None:
        super().__init__()
        self.data: deque[bytes | Callable] = deque()

    # noinspection PyUnusedLocal
    def read(self, *args):
        with self.handshake():
            if not self.data:
                return b""
            data = self.data.popleft()
            return data() if callable(data) else data


class FakeOutput(_TestableWithHandshake):
    """Common output/http-server/progress interface, for caching all write() calls and simulating write errors"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.data: list[bytes] = []

    def write(self, data):
        with self.handshake():
            return self._write(data)

    def _write(self, data):
        self.data.append(data)


class FakePlayerOutput(FakeOutput, PlayerOutput):
    def open(self):
        with patch("streamlink_cli.output.player.which", side_effect=lambda path: path):
            return super().open()


class FakeFileOutput(FakeOutput, FileOutput):
    pass


class FakeHTTPOutput(FakeOutput, HTTPOutput):
    pass


class FakeProgress(FakeOutput, Progress):
    # we're not interested in any application logic of the Progress class
    update = print_end = lambda *_, **__: None


class FakeStreamRunner(StreamRunner):
    # override and remove optional typing annotations
    playerpoller: EventedPlayerPollThread
    progress: FakeProgress


@pytest.fixture(autouse=True)
def _logging(caplog: pytest.LogCaptureFixture):
    assert streamrunnerlogger.name == "streamlink.cli"
    caplog.set_level(1, "streamlink")


@pytest.fixture()
def stream():
    stream = FakeStream()
    yield stream
    assert stream.closed


# "stream_runner" fixture dependency declared in downstream scopes
@pytest.fixture()
def runnerthread(request: pytest.FixtureRequest, stream_runner: StreamRunner):
    class RunnerThread(Thread):
        exception = None

        def run(self):
            try:
                super().run()
            except BaseException as err:
                self.exception = err

    thread = RunnerThread(
        daemon=True,
        name="Runner thread",
        target=stream_runner.run,
        args=(b"prebuffer",),
    )
    yield thread

    assert_thread_termination(thread, "Runner thread has terminated")

    exception = getattr(request, "param", {}).get("exception", None)
    assert isinstance(thread.exception, type(exception))
    assert str(thread.exception) == str(exception)


async def assert_handshake_steps(*items: _TestableWithHandshake) -> None:
    for item in items:
        assert await item.handshake.asyncstep(TIMEOUT_AWAIT_HANDSHAKE) is True


def assert_thread_termination(thread: Thread, assertion: str):
    thread.join(TIMEOUT_AWAIT_THREADJOIN)
    assert not thread.is_alive(), assertion


class TestPlayerOutput:
    @pytest.fixture()
    def player_process(self):
        player_process = Mock()
        player_process.poll = Mock(return_value=None)

        return player_process

    @pytest.fixture()
    def output(self, monkeypatch: pytest.MonkeyPatch, player_process: Mock):
        mock_popen = Mock(return_value=player_process)
        monkeypatch.setattr("subprocess.Popen", mock_popen)
        monkeypatch.setattr("streamlink_cli.output.player.sleep", Mock())

        output = FakePlayerOutput(Path("mocked"))
        output.open()
        try:
            yield output
        finally:
            output.close()

    @pytest.fixture()
    def stream_runner(self, monkeypatch: pytest.MonkeyPatch, stream: FakeStream, output: FakePlayerOutput):
        monkeypatch.setattr("streamlink_cli.streamrunner.PlayerPollThread", EventedPlayerPollThread)
        stream_runner = StreamRunner(stream, output)
        assert isinstance(stream_runner.playerpoller, EventedPlayerPollThread)
        assert not stream_runner.playerpoller.is_alive()
        assert not isinstance(stream_runner.output, HTTPOutput)
        assert not stream_runner.progress
        yield stream_runner
        assert not stream_runner.playerpoller.is_alive()

    @pytest.mark.trio()
    async def test_read_write(
        self,
        caplog: pytest.LogCaptureFixture,
        runnerthread: Thread,
        stream_runner: FakeStreamRunner,
        stream: FakeStream,
        output: FakePlayerOutput,
    ):
        stream.data.extend((b"foo", b"bar"))

        runnerthread.start()
        assert output.data == []

        # write prebuffer
        await assert_handshake_steps(output)
        assert output.data == [b"prebuffer"]

        # read and write next chunk
        await assert_handshake_steps(stream, output)
        assert output.data == [b"prebuffer", b"foo"]

        # poll player process
        await assert_handshake_steps(stream_runner.playerpoller)
        assert stream_runner.playerpoller.is_alive()

        # read and write next chunk
        await assert_handshake_steps(stream, output)
        assert output.data == [b"prebuffer", b"foo", b"bar"]

        assert not stream.closed, "Stream is not closed"

        # read stream end
        await assert_handshake_steps(stream)
        assert output.data == [b"prebuffer", b"foo", b"bar"]

        # wait for runner thread to terminate first before asserting log records
        assert_thread_termination(runnerthread, "Runner thread has terminated")
        assert [(record.module, record.levelname, record.message) for record in caplog.records] == [
            ("streamrunner", "info", "Stream ended"),
        ]

    @pytest.mark.trio()
    async def test_paused(
        self,
        caplog: pytest.LogCaptureFixture,
        runnerthread: Thread,
        stream_runner: FakeStreamRunner,
        stream: FakeStream,
        output: FakePlayerOutput,
    ):
        delayed = Handshake()

        def item():
            with delayed():
                return b"delayed"

        stream.data.append(item)

        runnerthread.start()
        assert output.data == []

        # write prebuffer
        await assert_handshake_steps(output)
        assert output.data == [b"prebuffer"]
        assert not delayed.wait_ready(0), "Delayed chunk has not been read yet"

        # attempt reading delayed chunk
        stream.handshake.go()
        assert delayed.wait_ready(TIMEOUT_AWAIT_HANDSHAKE), "read() call of delayed chunk is paused"
        assert output.data == [b"prebuffer"]

        assert not stream.closed, "Stream is not closed"

        # poll player process
        await assert_handshake_steps(stream_runner.playerpoller)
        assert stream_runner.playerpoller.is_alive()

        # unpause delayed chunk
        delayed.go()
        assert stream.handshake.wait_done(TIMEOUT_AWAIT_HANDSHAKE), "Delayed chunk has successfully been read"
        await assert_handshake_steps(output)
        assert output.data == [b"prebuffer", b"delayed"]

        assert not stream.closed, "Stream is not closed"

        # read stream end
        await assert_handshake_steps(stream)
        assert output.data == [b"prebuffer", b"delayed"]

        # wait for runner thread to terminate first before asserting log records
        assert_thread_termination(runnerthread, "Runner thread has terminated")
        assert [(record.module, record.levelname, record.message) for record in caplog.records] == [
            ("streamrunner", "info", "Stream ended"),
        ]

    @pytest.mark.trio()
    @pytest.mark.parametrize(
        ("writeerror", "runnerthread"),
        [
            pytest.param(
                OSError(errno.EPIPE, "Broken pipe"),
                {},
                id="Acceptable error: EPIPE",
            ),
            pytest.param(
                OSError(errno.EINVAL, "Invalid argument"),
                {},
                id="Acceptable error: EINVAL",
            ),
            pytest.param(
                OSError(errno.ECONNRESET, "Connection reset"),
                {},
                id="Acceptable error: ECONNRESET",
            ),
            pytest.param(
                OSError("Unknown error"),
                {"exception": OSError("Error when writing to output: Unknown error, exiting")},
                id="Non-acceptable error",
            ),
        ],
        indirect=["runnerthread"],
    )
    async def test_player_close(
        self,
        caplog: pytest.LogCaptureFixture,
        runnerthread: Thread,
        stream_runner: FakeStreamRunner,
        stream: FakeStream,
        output: FakePlayerOutput,
        player_process: Mock,
        writeerror: Exception,
    ):
        stream.data.extend((b"foo", b"bar"))

        runnerthread.start()
        assert output.data == []

        # write prebuffer
        await assert_handshake_steps(output)
        assert output.data == [b"prebuffer"]

        # poll player process
        await assert_handshake_steps(stream_runner.playerpoller)
        assert stream_runner.playerpoller.is_alive()

        # read and write next chunk
        await assert_handshake_steps(stream, output)
        assert output.data == [b"prebuffer", b"foo"]

        assert not stream.closed, "Stream is not closed yet"

        # close player
        with patch.object(output, "_write", side_effect=writeerror):
            # let player process terminate with code 0 and poll process once
            player_process.poll.return_value = 0
            await assert_handshake_steps(stream_runner.playerpoller)
            assert_thread_termination(stream_runner.playerpoller, "Polling has stopped after player process terminated")

            assert stream.closed, "Stream got closed after the player was closed"

            # read and write next chunk (write will now also raise)
            await assert_handshake_steps(stream, output)
            assert output.data == [b"prebuffer", b"foo"]

        # wait for runner thread to terminate first before asserting log records
        assert_thread_termination(runnerthread, "Runner thread has terminated")
        assert [(record.module, record.levelname, record.message) for record in caplog.records] == [
            ("streamrunner", "info", "Player closed"),
            ("streamrunner", "info", "Stream ended"),
        ]

    @pytest.mark.trio()
    async def test_player_close_paused(
        self,
        caplog: pytest.LogCaptureFixture,
        runnerthread: Thread,
        stream_runner: FakeStreamRunner,
        stream: FakeStream,
        output: FakePlayerOutput,
        player_process: Mock,
    ):
        delayed = Handshake()

        def item():
            with delayed():
                return b""

        stream.data.append(item)

        runnerthread.start()
        assert output.data == []

        # write prebuffer
        await assert_handshake_steps(output)
        assert output.data == [b"prebuffer"]
        assert not delayed.wait_ready(0), "Delayed chunk has not been read yet"

        # poll player process
        await assert_handshake_steps(stream_runner.playerpoller)
        assert stream_runner.playerpoller.is_alive()

        stream.handshake.go()
        assert delayed.wait_ready(TIMEOUT_AWAIT_HANDSHAKE), "read() call of delayed chunk is paused"
        assert output.data == [b"prebuffer"]

        assert not stream.closed, "Stream is not closed yet"

        # let player process terminate with code 0 and poll process once
        player_process.poll.return_value = 0
        await assert_handshake_steps(stream_runner.playerpoller)
        assert_thread_termination(stream_runner.playerpoller, "Polling has stopped after player process terminated")

        assert stream.closed, "Stream got closed after the player was closed, even if the stream was paused"

        # unpause delayed chunk (stream end)
        delayed.go()
        assert stream.handshake.wait_done(TIMEOUT_AWAIT_HANDSHAKE), "Delayed chunk has successfully been read"
        assert output.data == [b"prebuffer"]

        # wait for runner thread to terminate first before asserting log records
        assert_thread_termination(runnerthread, "Runner thread has terminated")
        assert [(record.module, record.levelname, record.message) for record in caplog.records] == [
            ("streamrunner", "info", "Player closed"),
            ("streamrunner", "info", "Stream ended"),
        ]

    @pytest.mark.trio()
    @pytest.mark.parametrize(
        "runnerthread",
        [{"exception": OSError("Error when reading from stream: Read timeout, exiting")}],
        indirect=["runnerthread"],
    )
    async def test_readerror(
        self,
        caplog: pytest.LogCaptureFixture,
        runnerthread: Thread,
        stream_runner: FakeStreamRunner,
        stream: FakeStream,
        output: FakePlayerOutput,
    ):
        # make next read() call raise a read-timeout error
        stream.data.append(Mock(side_effect=OSError("Read timeout")))

        runnerthread.start()
        assert output.data == []

        # write prebuffer
        await assert_handshake_steps(output)
        assert output.data == [b"prebuffer"]

        # poll player process
        await assert_handshake_steps(stream_runner.playerpoller)
        assert stream_runner.playerpoller.is_alive()

        # read stream (will raise a read timeout)
        await assert_handshake_steps(stream)

        # poll player process again
        await assert_handshake_steps(stream_runner.playerpoller)
        assert_thread_termination(stream_runner.playerpoller, "Polling has stopped on read error")

        # wait for runner thread to terminate first before asserting log records
        assert_thread_termination(runnerthread, "Runner thread has terminated")
        assert [(record.module, record.levelname, record.message) for record in caplog.records] == [
            ("streamrunner", "info", "Stream ended"),
        ]


class TestHTTPServer:
    @pytest.fixture()
    def output(self):
        return FakeHTTPOutput()

    @pytest.fixture()
    def stream_runner(self, stream: FakeStream, output: FakeHTTPOutput):
        stream_runner = StreamRunner(stream, output)
        assert not stream_runner.playerpoller
        assert not stream_runner.progress
        assert isinstance(stream_runner.output, HTTPOutput)
        return stream_runner

    @pytest.mark.trio()
    async def test_read_write(
        self,
        caplog: pytest.LogCaptureFixture,
        runnerthread: Thread,
        stream_runner: FakeStreamRunner,
        stream: FakeStream,
        output: FakeHTTPOutput,
    ):
        stream.data.extend((b"foo", b"bar"))

        runnerthread.start()
        assert output.data == []

        # write prebuffer
        await assert_handshake_steps(output)
        assert output.data == [b"prebuffer"]

        # read and write next chunk
        await assert_handshake_steps(stream, output)
        assert output.data == [b"prebuffer", b"foo"]

        # read and write next chunk
        await assert_handshake_steps(stream, output)
        assert output.data == [b"prebuffer", b"foo", b"bar"]

        assert not stream.closed, "Stream is not closed"

        # read stream end
        await assert_handshake_steps(stream)
        assert output.data == [b"prebuffer", b"foo", b"bar"]

        # wait for runner thread to terminate first before asserting log records
        assert_thread_termination(runnerthread, "Runner thread has terminated")
        assert [(record.module, record.levelname, record.message) for record in caplog.records] == [
            ("streamrunner", "info", "Stream ended"),
        ]

    @pytest.mark.parametrize(
        ("writeerror", "logs", "runnerthread"),
        [
            pytest.param(
                OSError(errno.EPIPE, "Broken pipe"),
                True,
                {},
                id="Acceptable error: EPIPE",
            ),
            pytest.param(
                OSError(errno.EINVAL, "Invalid argument"),
                True,
                {},
                id="Acceptable error: EINVAL",
            ),
            pytest.param(
                OSError(errno.ECONNRESET, "Connection reset"),
                True,
                {},
                id="Acceptable error: ECONNRESET",
            ),
            pytest.param(
                OSError("Unknown error"),
                False,
                {"exception": OSError("Error when writing to output: Unknown error, exiting")},
                id="Non-acceptable error",
            ),
        ],
        indirect=["runnerthread"],
    )
    def test_writeerror(
        self,
        caplog: pytest.LogCaptureFixture,
        runnerthread: Thread,
        stream_runner: FakeStreamRunner,
        stream: FakeStream,
        output: FakePlayerOutput,
        logs: bool,
        writeerror: Exception,
    ):
        runnerthread.start()

        with patch.object(output, "_write", side_effect=writeerror):
            assert output.handshake.step(TIMEOUT_AWAIT_HANDSHAKE)
            assert output.data == []

        # wait for runner thread to terminate first before asserting log records
        assert_thread_termination(runnerthread, "Runner thread has terminated")
        expectedlogs = (
            ([("streamrunner", "info", "HTTP connection closed")] if logs else [])
            + [("streamrunner", "info", "Stream ended")]
        )  # fmt: skip
        assert [(record.module, record.levelname, record.message) for record in caplog.records] == expectedlogs


class TestProgress:
    @pytest.fixture()
    def output(self):
        return FakeFileOutput(Path("filename"))

    @pytest.fixture()
    def progress(self):
        return FakeProgress(console=Mock(), path=Path("filename"))

    @pytest.fixture()
    def stream_runner(self, stream: FakeStream, output: FakeFileOutput, progress: FakeProgress):
        stream_runner = FakeStreamRunner(stream, output, progress=progress)
        assert not stream_runner.playerpoller
        assert stream_runner.progress is progress
        assert not stream_runner.progress.is_alive()
        yield stream_runner
        assert not stream_runner.progress.is_alive()

    @pytest.mark.trio()
    async def test_read_write(
        self,
        caplog: pytest.LogCaptureFixture,
        runnerthread: Thread,
        stream_runner: FakeStreamRunner,
        stream: FakeStream,
        output: FakeFileOutput,
    ):
        stream.data.extend((b"foo", b"bar"))

        runnerthread.start()
        assert output.data == []

        # write prebuffer
        await assert_handshake_steps(output, stream_runner.progress)
        assert output.data == [b"prebuffer"]
        assert stream_runner.progress.data == [b"prebuffer"]

        # read and write next chunk
        await assert_handshake_steps(stream, output, stream_runner.progress)
        assert output.data == [b"prebuffer", b"foo"]
        assert stream_runner.progress.data == [b"prebuffer", b"foo"]

        # read and write next chunk
        await assert_handshake_steps(stream, output, stream_runner.progress)
        assert output.data == [b"prebuffer", b"foo", b"bar"]
        assert stream_runner.progress.data == [b"prebuffer", b"foo", b"bar"]

        assert not stream.closed, "Stream is not closed"

        # read stream end
        await assert_handshake_steps(stream)
        assert output.data == [b"prebuffer", b"foo", b"bar"]
        assert stream_runner.progress.data == [b"prebuffer", b"foo", b"bar"]

        # wait for runner thread to terminate first before asserting log records
        assert_thread_termination(runnerthread, "Runner thread has terminated")
        assert [(record.module, record.levelname, record.message) for record in caplog.records] == [
            ("streamrunner", "info", "Stream ended"),
        ]
