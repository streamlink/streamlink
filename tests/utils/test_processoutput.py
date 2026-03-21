from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from unittest.mock import Mock, call

import pytest
import trio
from trio.testing import wait_all_tasks_blocked

from streamlink.compat import ExceptionGroup
from streamlink.utils.processoutput import ProcessOutput


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from trio.testing import MockClock


TIME_TEST_MAX = 10

# language=python
CODE = """
import _codecs
import signal
import sys

if sys.argv[-1] == "ignoresigterm":
    signal.signal(signal.SIGTERM, signal.SIG_IGN)

while line := sys.stdin.buffer.readline():
    if line[:5] == b"exit:":
        raise SystemExit(int(line[5:-1]))
    stream = sys.stdout.buffer if line[:7] == b"stdout:" else sys.stderr.buffer
    line, _ = _codecs.escape_decode(line[7:-1])
    stream.write(line)
    stream.flush()
""".strip()


class FakeProcessOutput(ProcessOutput):
    onexit: Mock
    onstdout: Mock
    onstderr: Mock

    onoutput_sender: trio.MemorySendChannel[tuple[str, str]]
    onoutput_receiver: trio.MemoryReceiveChannel[tuple[str, str]]

    def __init__(self, *args, ignoresigterm: bool = False, **kwargs):
        command = [sys.executable, "-c", CODE]
        if ignoresigterm:
            command.append("ignoresigterm")
        kwargs.setdefault("command", command)

        super().__init__(*args, **kwargs)
        self.stream_receive_some_event = trio.Event()
        self.onoutput_sender, self.onoutput_receiver = trio.open_memory_channel(10)

        def onstdouterr(channel, meth):
            def _inner(*_args, **_kwargs):
                res = meth(*_args, **_kwargs)
                try:
                    return res
                finally:
                    self.onoutput_sender.send_nowait((channel, res))

            return _inner

        self.onexit = Mock(side_effect=self.onexit)
        self.onstdout = Mock(side_effect=onstdouterr("stdout", self.onstdout))
        self.onstderr = Mock(side_effect=onstdouterr("stderr", self.onstderr))

    async def _onoutput(self, callback: Callable[[int, str], bool | None], stream: trio.abc.ReceiveStream):
        async def stream_receive_some(*_args, **_kwargs):
            self.stream_receive_some_event.set()
            return await receive_some(*_args, **_kwargs)

        receive_some = stream.receive_some
        stream.receive_some = stream_receive_some  # type: ignore

        return await super()._onoutput(callback, stream)


@pytest.fixture()
async def _max_test_time(nursery: trio.Nursery, mock_clock: MockClock):  # noqa: RUF029
    async def timeout():  # pragma: no cover
        await trio.sleep(TIME_TEST_MAX)
        mock_clock.autojump_threshold = 0
        pytest.fail("Test timed out")

    nursery.start_soon(timeout)


@pytest.fixture()
def get_process(monkeypatch: pytest.MonkeyPatch, _max_test_time) -> Callable[[], Awaitable[trio.Process]]:
    trio_run_process = trio.run_process

    # use a memory channel, so we can wait until the process has launched
    sender: trio.MemorySendChannel[trio.Process]
    receiver: trio.MemoryReceiveChannel[trio.Process]
    sender, receiver = trio.open_memory_channel(1)

    async def get_process() -> trio.Process:
        return await receiver.receive()

    async def fake_trio_run_process(*args, task_status, **kwargs):
        task_status_started = task_status.started

        def fake_task_status_started(process: trio.Process):
            task_status_started(process)
            sender.send_nowait(process)

        # intercept the task status report
        task_status.started = fake_task_status_started

        return await trio_run_process(*args, task_status=task_status, **kwargs)

    monkeypatch.setattr("trio.run_process", fake_trio_run_process)

    return get_process


@pytest.mark.trio()
@pytest.mark.usefixtures("_max_test_time")
async def test_ontimeout(mock_clock: MockClock) -> None:
    po = FakeProcessOutput(timeout=2)
    result = None

    async def run():
        nonlocal result
        result = await po.arun()

    async with trio.open_nursery() as nursery:
        nursery.start_soon(run)
        await wait_all_tasks_blocked()
        assert result is None
        mock_clock.jump(4)

    assert result is False
    assert po.onexit.call_args_list == []
    assert po.onstdout.call_args_list == []
    assert po.onstderr.call_args_list == []


@pytest.mark.trio()
@pytest.mark.parametrize(
    ("exit_code", "expected"),
    [
        pytest.param(0, True, id="success"),
        pytest.param(1, False, id="failure"),
    ],
)
async def test_exit_code(get_process: Callable[[], Awaitable[trio.Process]], exit_code: int, expected: bool):
    po = FakeProcessOutput(timeout=4)
    result = None

    async def run():
        nonlocal result
        result = await po.arun()

    async with trio.open_nursery() as nursery:
        nursery.start_soon(run)
        process = await get_process()
        assert process.stdin
        await process.stdin.send_all(f"exit:{exit_code}\n".encode())

    assert result is expected
    assert po.onexit.call_args_list == [call(exit_code)]
    assert po.onstdout.call_args_list == []
    assert po.onstderr.call_args_list == []


@pytest.mark.trio()
async def test_stdout_stderr(get_process: Callable[[], Awaitable[trio.Process]]):
    po = FakeProcessOutput(timeout=4)
    result = None

    async def run():
        nonlocal result
        result = await po.arun()

    async with trio.open_nursery() as nursery:
        nursery.start_soon(run)
        process = await get_process()
        assert process.stdin
        assert po.onstdout.call_args_list == []
        assert po.onstderr.call_args_list == []

        await process.stdin.send_all(b"stdout:foo\\n\n")
        assert await po.onoutput_receiver.receive() == ("stdout", None)
        assert po.onstdout.call_args_list == [call(0, "foo")]
        assert po.onstderr.call_args_list == []

        await process.stdin.send_all(b"stdout:bar\\nbaz\\n\n")
        assert await po.onoutput_receiver.receive() == ("stdout", None)
        assert await po.onoutput_receiver.receive() == ("stdout", None)
        assert po.onstdout.call_args_list == [call(0, "foo"), call(1, "bar"), call(2, "baz")]
        assert po.onstderr.call_args_list == []

        await process.stdin.send_all(b"stderr:bar\\n\n")
        assert await po.onoutput_receiver.receive() == ("stderr", None)
        assert po.onstdout.call_args_list == [call(0, "foo"), call(1, "bar"), call(2, "baz")]
        assert po.onstderr.call_args_list == [call(0, "bar")]

        # order of items in receive stream is not guaranteed
        await process.stdin.send_all(b"stdout:123\\n\nstderr:456\\n\n")
        received = []
        for _ in range(2):
            received.append(await po.onoutput_receiver.receive())
        received.sort(key=lambda elem: elem[0])
        assert received == [("stderr", None), ("stdout", None)]

        await process.stdin.send_all(b"exit:0\n")

    assert result is True
    assert po.onexit.call_args_list == [call(0)]
    assert po.onstdout.call_args_list == [call(0, "foo"), call(1, "bar"), call(2, "baz"), call(3, "123")]
    assert po.onstderr.call_args_list == [call(0, "bar"), call(1, "456")]


@pytest.mark.trio()
@pytest.mark.parametrize(
    ("stdin", "expected"),
    [
        pytest.param(
            (b"stdout:foo\n", b"stdout:bar\\n\n"),
            ([call(0, "foobar")], [call(0, "foobar")]),
            id="line",
        ),
        pytest.param(
            # incomplete UTF-8 sequence of the bear-face emoji, followed by its remaining data and another incomplete one
            (b"stdout:\\xf0\\x9f\n", b"stdout:\\x90\\xbb\\n\\xf0\\x9f\n"),
            # final result includes the Unicode "replacement character" due to the buffer having an incomplete UTF-8 sequence
            ([call(0, "🐻")], [call(0, "🐻"), call(1, "\ufffd")]),
            id="utf8-sequence",
        ),
    ],
)
async def test_stdout_incomplete_chunks(
    get_process: Callable[[], Awaitable[trio.Process]],
    stdin: tuple[bytes, bytes],
    expected: tuple[list, list],
):
    po = FakeProcessOutput(timeout=4)
    po._receive_max_bytes = 1  # required for full code coverage
    result = None

    async def run():
        nonlocal result
        result = await po.arun()

    async with trio.open_nursery() as nursery:
        nursery.start_soon(run)
        process = await get_process()
        assert process.stdin
        assert po.onstdout.call_args_list == []

        await process.stdin.send_all(stdin[0])
        await po.stream_receive_some_event.wait()
        assert po.onoutput_sender.statistics().current_buffer_used == 0
        assert po.onstdout.call_args_list == []

        await process.stdin.send_all(stdin[1])
        assert await po.onoutput_receiver.receive() == ("stdout", None)
        assert po.onstdout.call_args_list == expected[0]

        await process.stdin.send_all(b"exit:0\n")

    assert result is True
    assert po.onexit.call_args_list == [call(0)]
    assert po.onstdout.call_args_list == expected[1]


@pytest.mark.trio()
@pytest.mark.parametrize(
    ("expected", "return_value"),
    [
        pytest.param("yes", True, id="success"),
        pytest.param("no", False, id="failure"),
    ],
)
@pytest.mark.parametrize("channel", ["stdout", "stderr"])
async def test_output_callback(
    get_process: Callable[[], Awaitable[trio.Process]],
    expected: str,
    return_value: bool,
    channel: str,
):
    class CustomProcessOutput(ProcessOutput):
        def onstdout(self, idx: int, line: str) -> bool:
            return line == expected

        def onstderr(self, idx: int, line: str) -> bool:
            return line == expected

    class CustomFakeProcessOutput(FakeProcessOutput, CustomProcessOutput):
        pass

    po = CustomFakeProcessOutput(timeout=4)
    result = None

    async def run():
        nonlocal result
        result = await po.arun()

    async with trio.open_nursery() as nursery:
        nursery.start_soon(run)
        process = await get_process()
        assert process.stdin

        await process.stdin.send_all(f"{channel}:yes\\n\n".encode())
        assert await po.onoutput_receiver.receive() == (channel, return_value)

        await process.stdin.send_all(b"exit:0\n")

    assert result is return_value
    assert po.onexit.call_args_list == []
    assert po.onstdout.call_args_list == ([call(0, "yes")] if channel == "stdout" else [])
    assert po.onstderr.call_args_list == ([call(0, "yes")] if channel == "stderr" else [])


@pytest.mark.trio()
async def test_output_exception(get_process: Callable[[], Awaitable[trio.Process]]):
    class CustomProcessOutput(ProcessOutput):
        def onstdout(self, idx: int, line: str) -> bool:
            raise ZeroDivisionError()

    class CustomFakeProcessOutput(FakeProcessOutput, CustomProcessOutput):
        pass

    po = CustomFakeProcessOutput(timeout=4)
    # noinspection PyUnusedLocal
    process: trio.Process | None = None

    with pytest.raises(ExceptionGroup) as exc_info:  # noqa: PT012
        async with trio.open_nursery() as nursery:
            nursery.start_soon(po.arun)
            process = await get_process()
            assert process.stdin

            await process.stdin.send_all(b"stdout:foo\\n\n")
            assert await po.onoutput_receiver.receive() == ("stdout", None)

    assert process
    assert process.poll() is not None
    assert exc_info.group_contains(ZeroDivisionError)


@pytest.mark.posix_only()
@pytest.mark.trio()
async def test_kill(monkeypatch: pytest.MonkeyPatch, mock_clock: MockClock, get_process: Callable[[], Awaitable[trio.Process]]):
    po = FakeProcessOutput(timeout=2, wait_terminate=4, ignoresigterm=True)
    result = None

    async def run():
        nonlocal result
        result = await po.arun()

    async with trio.open_nursery() as nursery:
        nursery.start_soon(run)
        process = await get_process()
        assert process.poll() is None
        assert process.stdin

        # ensure that our Python subprocess has fully initialized and updated its SIGTERM signal handler
        await process.stdin.send_all(b"stdout:OK\\n\n")
        assert await po.onoutput_receiver.receive() == ("stdout", None)
        assert po.onstdout.call_args_list == [call(0, "OK")]
        po.onstdout.call_args_list.clear()

        mock_terminate = Mock(side_effect=process.terminate)
        mock_kill = Mock(side_effect=process.kill)
        monkeypatch.setattr(process, "terminate", mock_terminate)
        monkeypatch.setattr(process, "kill", mock_kill)

        mock_clock.jump(po.timeout)

        await wait_all_tasks_blocked()
        assert process.poll() is None

        assert mock_terminate.call_count == 1
        assert mock_kill.call_count == 0

        await wait_all_tasks_blocked()
        assert process.poll() is None

        mock_clock.jump(po.wait_terminate)
        await wait_all_tasks_blocked()
        assert mock_terminate.call_count == 1
        assert mock_kill.call_count == 1

        mock_clock.rate = 1

    assert result is False
    assert po.onexit.call_args_list == []
    assert po.onstdout.call_args_list == []
    assert po.onstderr.call_args_list == []
