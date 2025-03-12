from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from subprocess import PIPE
from unittest.mock import Mock

import pytest
import trio

from streamlink.webbrowser.webbrowser import Webbrowser


@pytest.fixture()
def caplog(caplog: pytest.LogCaptureFixture):
    caplog.set_level(1, "streamlink")
    return caplog


@pytest.fixture(autouse=True)
def resolve_executable(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    return_value = getattr(request, "param", "default")
    monkeypatch.setattr("streamlink.webbrowser.webbrowser.resolve_executable", Mock(return_value=return_value))
    return return_value


@pytest.fixture()
def webbrowser_launch(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture):
    trio_run_process = trio.run_process

    # use a memory channel, so we can wait until the process has launched
    sender: trio.MemorySendChannel[trio.Process]
    receiver: trio.MemoryReceiveChannel[trio.Process]
    sender, receiver = trio.open_memory_channel(1)

    async def fake_trio_run_process(*args, task_status, **kwargs):
        task_status_started = task_status.started

        def fake_task_status_started(process: trio.Process):
            task_status_started(process)
            sender.send_nowait(process)

        # intercept the task status report
        task_status.started = fake_task_status_started
        # override the stdin parameter, so we can send data to our dummy process
        kwargs["stdin"] = PIPE

        return await trio_run_process(*args, task_status=task_status, **kwargs)

    monkeypatch.setattr("trio.run_process", fake_trio_run_process)

    @asynccontextmanager
    async def webbrowser_launch(*args, webbrowser: Webbrowser | None = None, **kwargs):
        # dummy web browser process, which idles until stdin receives input with an exit code
        webbrowser = webbrowser or Webbrowser()
        webbrowser.executable = sys.executable
        webbrowser.arguments = ["-c", "import sys; sys.exit(int(sys.stdin.readline()))", *webbrowser.arguments]

        headless = kwargs.get("headless", False)

        async with webbrowser.launch(*args, **kwargs) as nursery:
            assert isinstance(nursery, trio.Nursery)
            assert [(record.name, record.levelname, record.msg) for record in caplog.records] == [
                (
                    "streamlink.webbrowser.webbrowser",
                    "info",
                    f"Launching web browser: {sys.executable} ({headless=})",
                ),
            ]
            caplog.records.clear()
            # wait until the process has launched, so we can test it
            process = await receiver.receive()
            yield nursery, process

    return webbrowser_launch
