import asyncio
from collections import deque
from typing import Iterable, Optional

import freezegun
import pytest
import pytest_asyncio

from streamlink.utils.processoutput import ProcessOutput


try:
    from unittest.mock import AsyncMock, Mock, call, patch  # type: ignore
except ImportError:
    # noinspection PyUnresolvedReferences
    from mock import AsyncMock, Mock, call, patch  # type: ignore


class AsyncIterator:
    def __init__(self, event_loop: asyncio.BaseEventLoop, iterable: Optional[Iterable] = None):
        self._loop = event_loop
        self._deque = deque(iterable or ())
        self._newfuture()

    def append(self, item):
        self._deque.append(item)
        self._setfutureresult()

    def extend(self, iterable: Iterable):
        self._deque.extend(iterable)
        self._setfutureresult()

    def _newfuture(self):
        self._future = self._loop.create_future()

    def _setfutureresult(self):
        if len(self._deque) and not self._future.done():
            self._future.set_result(True)

    def __aiter__(self):
        return self

    async def __anext__(self):
        while True:
            await self._future
            try:
                return self._deque.popleft()
            except IndexError:
                self._newfuture()


class FakeProcessOutput(ProcessOutput):
    onexit: Mock
    onstdout: Mock
    onstderr: Mock


@pytest.fixture()
def mock_process(event_loop: asyncio.BaseEventLoop):
    process = Mock(asyncio.subprocess.Process)
    process.stdout = AsyncIterator(event_loop)
    process.stderr = AsyncIterator(event_loop)

    return process


@pytest.fixture()
def processoutput(request, mock_process):
    class MyProcessOutput(FakeProcessOutput):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.onexit = Mock(wraps=self.onexit)
            self.onstdout = Mock(wraps=self.onstdout)
            self.onstderr = Mock(wraps=self.onstderr)

    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_process)) as mock_create_subprocess_exec:
        yield MyProcessOutput(["foo", "bar"], **getattr(request, "param", {}))

    mock_create_subprocess_exec.assert_awaited_once_with(
        "foo",
        "bar",
        stdin=None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )


@pytest_asyncio.fixture(autouse=True)
async def assert_tasks_cleanup(event_loop: asyncio.BaseEventLoop):
    yield
    current_task = asyncio.current_task(event_loop)
    assert not [task for task in asyncio.all_tasks(event_loop) if task is not current_task]
    await event_loop.shutdown_asyncgens()


@pytest.mark.asyncio()
@pytest.mark.parametrize("processoutput", [{"timeout": 1}], indirect=True)
async def test_ontimeout(event_loop: asyncio.BaseEventLoop, processoutput: FakeProcessOutput, mock_process: Mock):
    with freezegun.freeze_time("2000-01-01T00:00:00.000Z") as frozen_time:
        fut_process_wait = event_loop.create_future()
        mock_process.wait = Mock(return_value=fut_process_wait)

        async def advance_time():
            # required for making the run-task await the "done" future
            await asyncio.sleep(0)
            frozen_time.tick(2)

        task_run = asyncio.create_task(processoutput._run())
        task_time = asyncio.create_task(advance_time())
        await asyncio.wait({task_run, task_time}, return_when=asyncio.FIRST_COMPLETED)

        assert mock_process.wait.called, "Has run the onexit callback and called process.wait()"
        assert not mock_process.kill.called, "Has not killed the process yet"

        result = await task_run

    assert result is False
    assert not processoutput.onexit.called
    assert not processoutput.onstdout.called
    assert not processoutput.onstderr.called
    assert fut_process_wait.cancelled()
    assert mock_process.kill.called


@pytest.mark.asyncio()
@pytest.mark.parametrize("processoutput", [{"timeout": 1}], indirect=True)
async def test_ontimeout_onexit(event_loop: asyncio.BaseEventLoop, processoutput: FakeProcessOutput, mock_process: Mock):
    fut_process_wait = event_loop.create_future()
    mock_process.wait = Mock(return_value=fut_process_wait)

    with freezegun.freeze_time("2000-01-01T00:00:00.000Z") as frozen_time:
        async def advance_time():
            # required for making the run-task await the "done" future
            await asyncio.sleep(0)
            frozen_time.tick(0.5)

        task_run = asyncio.create_task(processoutput._run())
        task_time = asyncio.create_task(advance_time())
        await asyncio.wait({task_run, task_time}, return_when=asyncio.FIRST_COMPLETED)

        assert mock_process.wait.called, "Has run the onexit callback and called process.wait()"
        assert not mock_process.kill.called, "Has not killed the process yet"

        # make the process return code 0 while waiting for the timeout
        fut_process_wait.set_result(0)

        # advance time again (the "done" future will already have a result set and the timeout task be cancelled)
        frozen_time.tick(1)  # type: ignore[arg-type]  # float/int are supported...

        result = await task_run

    assert result is True
    assert processoutput.onexit.called
    assert not processoutput.onstdout.called
    assert not processoutput.onstderr.called
    assert fut_process_wait.done()
    assert mock_process.kill.called


@pytest.mark.asyncio()
@pytest.mark.parametrize(("code", "expected"), [(0, True), (1, False)])
async def test_onexit(event_loop: asyncio.BaseEventLoop, processoutput: FakeProcessOutput, mock_process: Mock, code, expected):
    mock_process.wait = AsyncMock(return_value=code)

    result = await processoutput._run()

    assert result is expected
    assert processoutput.onexit.called
    assert not processoutput.onstdout.called
    assert not processoutput.onstderr.called
    assert mock_process.kill.called


@pytest.mark.asyncio()
@pytest.mark.parametrize("returnvalue", [True, False])
async def test_onoutput(event_loop: asyncio.BaseEventLoop, processoutput: FakeProcessOutput, mock_process: Mock, returnvalue):
    mock_process.wait = Mock(return_value=event_loop.create_future())
    mock_process.stdout.extend([b"foo", b"bar", b"baz"])

    def onstdout(idx: int, line: str):
        if idx < 3:
            mock_process.stderr.append(line.upper().encode())

    def onstderr(idx: int, line: str):
        mock_process.stdout.append(line[::-1].encode())
        if idx == 1:
            return returnvalue

    processoutput.onstdout = Mock(wraps=onstdout)
    processoutput.onstderr = Mock(wraps=onstderr)

    result = await processoutput._run()

    assert result is returnvalue
    assert not processoutput.onexit.called
    assert processoutput.onstdout.call_args_list == [
        call(0, "foo"),
        call(1, "bar"),
        call(2, "baz"),
        call(3, "OOF"),
        call(4, "RAB"),
    ]
    assert processoutput.onstderr.call_args_list == [
        call(0, "FOO"),
        call(1, "BAR"),
    ]
    assert mock_process.kill.called


@pytest.mark.asyncio()
async def test_onoutput_exception(event_loop: asyncio.BaseEventLoop, processoutput: FakeProcessOutput, mock_process: Mock):
    mock_process.wait = Mock(return_value=event_loop.create_future())
    mock_process.stdout.extend([b"foo", b"bar", b"baz"])

    error = ValueError("error")
    processoutput.onstdout = Mock(side_effect=error)

    with pytest.raises(ValueError) as cm:  # noqa: PT011
        await processoutput._run()

    assert cm.value is error
    assert not processoutput.onexit.called
    assert processoutput.onstdout.call_args_list == [call(0, "foo")]
    assert processoutput.onstderr.call_args_list == []
    assert mock_process.kill.called
