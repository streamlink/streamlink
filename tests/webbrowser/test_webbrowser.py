from __future__ import annotations

from contextlib import AbstractContextManager, nullcontext
from pathlib import Path
from signal import SIGTERM
from typing import List, Optional

import pytest
import trio

from streamlink.compat import is_win32
from streamlink.webbrowser.exceptions import WebbrowserError
from streamlink.webbrowser.webbrowser import Webbrowser


class _FakeWebbrowser(Webbrowser):
    @classmethod
    def launch_args(cls) -> List[str]:
        return ["foo", "bar"]


class TestInit:
    @pytest.mark.parametrize(("executable", "resolve_executable", "raises"), [
        pytest.param(
            None,
            None,
            pytest.raises(WebbrowserError, match="Could not resolve web browser executable"),
            id="Failure with default path",
        ),
        pytest.param(
            "custom",
            None,
            pytest.raises(WebbrowserError, match="Could not resolve web browser executable: custom"),
            id="Failure with custom path",
        ),
        pytest.param(
            None,
            "default",
            nullcontext(),
            id="Success with default path",
        ),
        pytest.param(
            "custom",
            "custom",
            nullcontext(),
            id="Success with custom path",
        ),
    ], indirect=["resolve_executable"])
    def test_resolve_executable(self, resolve_executable, executable: Optional[str], raises: nullcontext):
        with raises:
            Webbrowser(executable=executable)

    def test_arguments(self):
        webbrowser = _FakeWebbrowser()
        assert webbrowser.executable == "default"
        assert webbrowser.arguments == ["foo", "bar"]
        assert webbrowser.arguments is not _FakeWebbrowser.launch_args()


class TestLaunch:
    @pytest.mark.trio()
    async def test_terminate_on_nursery_exit(self, caplog: pytest.LogCaptureFixture, webbrowser_launch):
        nursery: trio.Nursery
        process: trio.Process
        async with webbrowser_launch() as (nursery, process):  # noqa: F841
            assert process.poll() is None, "process is still running"

        assert process.poll() == (1 if is_win32 else -SIGTERM), "Process has been terminated"
        assert [(record.name, record.levelname, record.msg) for record in caplog.records] == [
            ("streamlink.webbrowser.webbrowser", "debug", "Waiting for web browser process to terminate"),
        ]

    @pytest.mark.trio()
    async def test_terminate_on_nursery_cancellation(self, caplog: pytest.LogCaptureFixture, webbrowser_launch):
        nursery: trio.Nursery
        process: trio.Process
        async with webbrowser_launch() as (nursery, process):
            assert process.poll() is None, "process is still running"
            nursery.cancel_scope.cancel()

        assert process.poll() == (1 if is_win32 else -SIGTERM), "Process has been terminated"
        assert [(record.name, record.levelname, record.msg) for record in caplog.records] == [
            ("streamlink.webbrowser.webbrowser", "debug", "Waiting for web browser process to terminate"),
        ]

    @pytest.mark.trio()
    async def test_terminate_on_nursery_timeout(self, caplog: pytest.LogCaptureFixture, mock_clock, webbrowser_launch):
        nursery: trio.Nursery
        process: trio.Process
        async with webbrowser_launch(timeout=10) as (nursery, process):  # noqa: F841
            assert process.poll() is None, "process is still running"
            mock_clock.jump(20)
            await trio.sleep(0)

        assert process.poll() == (1 if is_win32 else -SIGTERM), "Process has been terminated"
        assert [(record.name, record.levelname, record.msg) for record in caplog.records] == [
            ("streamlink.webbrowser.webbrowser", "warning", "Web browser task group has timed out"),
            ("streamlink.webbrowser.webbrowser", "debug", "Waiting for web browser process to terminate"),
        ]

    @pytest.mark.trio()
    async def test_terminate_on_nursery_baseexception(self, caplog: pytest.LogCaptureFixture, webbrowser_launch):
        class FakeBaseException(BaseException):
            pass

        nursery: trio.Nursery
        process: trio.Process
        with pytest.raises(FakeBaseException):  # noqa: PT012
            async with webbrowser_launch() as (nursery, process):  # noqa: F841
                assert process.poll() is None, "process is still running"
                raise FakeBaseException()

        assert process.poll() == (1 if is_win32 else -SIGTERM), "Process has been terminated"
        assert [(record.name, record.levelname, record.msg) for record in caplog.records] == [
            ("streamlink.webbrowser.webbrowser", "debug", "Waiting for web browser process to terminate"),
        ]

    # don't run on Windows, because of some weird flaky subprocess early-termination issues
    @pytest.mark.posix_only()
    @pytest.mark.trio()
    # don't check for non-zero exit codes - we don't care
    @pytest.mark.parametrize("exit_code", [0, 1])
    async def test_process_ended_early(self, caplog: pytest.LogCaptureFixture, webbrowser_launch, exit_code):
        nursery: trio.Nursery
        process: trio.Process
        async with webbrowser_launch(timeout=10) as (nursery, process):  # noqa: F841
            assert process.poll() is None, "process is still running"
            assert process.stdin
            await process.stdin.send_all(str(exit_code).encode() + b"\r\n")
            await trio.sleep(5)

        assert process.poll() == exit_code, "Process has ended with the right exit code"
        assert [(record.name, record.levelname, record.msg) for record in caplog.records] == [
            ("streamlink.webbrowser.webbrowser", "warning", "Web browser process ended early"),
        ]


def test_temp_dir():
    webbrowser = Webbrowser()
    temp_dir = webbrowser._create_temp_dir()
    assert isinstance(temp_dir, AbstractContextManager)
    with temp_dir as path:
        assert Path(path).exists()
    assert not Path(path).exists()
