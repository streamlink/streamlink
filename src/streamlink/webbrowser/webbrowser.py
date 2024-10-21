from __future__ import annotations

import logging
import sys
import tempfile
from collections.abc import AsyncGenerator, Generator
from contextlib import AbstractAsyncContextManager, asynccontextmanager, contextmanager
from functools import partial
from pathlib import Path
from subprocess import DEVNULL

import trio

from streamlink.compat import BaseExceptionGroup
from streamlink.utils.path import resolve_executable
from streamlink.webbrowser.exceptions import WebbrowserError


log = logging.getLogger(__name__)


class Webbrowser:
    ERROR_RESOLVE = "Could not find web browser executable"

    TIMEOUT = 10

    @classmethod
    def names(cls) -> list[str]:
        return []

    @classmethod
    def fallback_paths(cls) -> list[str | Path]:
        return []

    @classmethod
    def launch_args(cls) -> list[str]:
        return []

    def __init__(self, executable: str | None = None):
        resolved = resolve_executable(executable, self.names(), self.fallback_paths())
        if not resolved:
            raise WebbrowserError(
                f"Invalid web browser executable: {executable}"
                if executable
                else f"{self.ERROR_RESOLVE}: Please set the path to a supported web browser using --webbrowser-executable",
            )

        self.executable: str | Path = resolved
        self.arguments: list[str] = self.launch_args().copy()

    def launch(self, headless: bool = False, timeout: float | None = None) -> AbstractAsyncContextManager[trio.Nursery]:
        return self._launch(self.executable, self.arguments, headless=headless, timeout=timeout)

    def _launch(
        self,
        executable: str | Path,
        arguments: list[str],
        headless: bool = False,
        timeout: float | None = None,
    ) -> AbstractAsyncContextManager[trio.Nursery]:
        if timeout is None:
            timeout = self.TIMEOUT

        launcher = _WebbrowserLauncher(executable, arguments, headless, timeout)

        # noinspection PyArgumentList
        return launcher.launch()

    @staticmethod
    @contextmanager
    def _create_temp_dir() -> Generator[str, None, None]:
        kwargs = {"ignore_cleanup_errors": True} if sys.version_info >= (3, 10) else {}
        with tempfile.TemporaryDirectory(**kwargs) as temp_file:  # type: ignore[call-overload]
            yield temp_file


class _WebbrowserLauncher:
    def __init__(self, executable: str | Path, arguments: list[str], headless: bool, timeout: float):
        self.executable = executable
        self.arguments = arguments
        self.headless = headless
        self.timeout = timeout
        self._process_ended_early = False

    @asynccontextmanager
    async def launch(self) -> AsyncGenerator[trio.Nursery, None]:
        try:
            headless = self.headless
            async with trio.open_nursery() as nursery:
                log.info(f"Launching web browser: {self.executable} ({headless=})")
                # the process is run in a separate task
                run_process = partial(
                    trio.run_process,
                    [self.executable, *self.arguments],
                    check=False,
                    stdout=DEVNULL,
                    stderr=DEVNULL,
                )
                # trio ensures that the process gets terminated when the task group gets cancelled
                process: trio.Process = await nursery.start(run_process)
                # the process watcher task cancels the entire task group when the user terminates/kills the process
                nursery.start_soon(self._task_process_watcher, process, nursery)
                try:
                    # the application logic is run here
                    with trio.move_on_after(self.timeout) as cancel_scope:
                        yield nursery
                    # check if the application logic has timed out
                    if cancel_scope.cancelled_caught:
                        log.warning("Web browser task group has timed out")
                finally:
                    # check if the task group hasn't been cancelled yet in the process watcher task
                    if not self._process_ended_early:
                        log.debug("Waiting for web browser process to terminate")
                    # once the application logic is done, cancel the entire task group and terminate/kill the process
                    nursery.cancel_scope.cancel()
        except BaseExceptionGroup as exc_grp:  # TODO: py310 support end: use except*
            exc: BaseException | BaseExceptionGroup | None = exc_grp.subgroup((KeyboardInterrupt, SystemExit))
            if not exc:  # not a KeyboardInterrupt or SystemExit
                raise
            while isinstance(exc, BaseExceptionGroup):  # get the first actual exception in the potentially nested groups
                exc = exc.exceptions[0]
            raise exc from exc.__context__

    async def _task_process_watcher(self, process: trio.Process, nursery: trio.Nursery) -> None:
        """Task for cancelling the launch task group if the user closes the browser or if it exits early on its own"""
        await process.wait()
        # if the task group hasn't been cancelled yet, then the application logic was still running
        if not nursery.cancel_scope.cancel_called:  # pragma: no branch
            self._process_ended_early = True
            log.warning("Web browser process ended early")
            nursery.cancel_scope.cancel()
