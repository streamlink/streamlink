from __future__ import annotations

import math
from collections.abc import Callable
from contextlib import suppress
from functools import partial
from subprocess import PIPE
from typing import BinaryIO

import trio


class ProcessOutput:
    _send_channel: trio.MemorySendChannel[bool]
    _receive_channel: trio.MemoryReceiveChannel[bool]

    def __init__(
        self,
        command: list[str],
        timeout: float = math.inf,
        wait_terminate: float = 2.0,
        stdin: int | bytes | BinaryIO | None = PIPE,
    ):
        self.command = command
        self.timeout = timeout
        self.wait_terminate = wait_terminate
        self.stdin = stdin
        self._send_channel, self._receive_channel = trio.open_memory_channel(1)

    def run(self) -> bool:  # pragma: no cover
        return trio.run(self.arun)

    async def arun(self) -> bool:
        with trio.move_on_after(self.timeout):
            async with trio.open_nursery() as nursery:
                run_process = partial(
                    trio.run_process,
                    self.command,
                    check=False,
                    capture_stdout=False,
                    capture_stderr=False,
                    stdin=self.stdin,
                    stdout=PIPE,
                    stderr=PIPE,
                    deliver_cancel=self._deliver_cancel,
                )
                process: trio.Process = await nursery.start(run_process)

                nursery.start_soon(self._onexit, process)
                nursery.start_soon(self._onoutput, self.onstdout, process.stdout)
                nursery.start_soon(self._onoutput, self.onstderr, process.stderr)

                res = await self._receive_channel.receive()
                nursery.cancel_scope.cancel()
                return res

        # noinspection PyUnreachableCode
        return False

    async def _deliver_cancel(self, proc: trio.Process):
        with suppress(OSError):
            proc.terminate()
            await trio.sleep(self.wait_terminate)
            proc.kill()

    async def _onexit(self, proc: trio.Process):
        code = await proc.wait()
        result = self.onexit(code)
        await self._send_channel.send(result)

    async def _onoutput(self, callback: Callable[[int, str], bool | None], stream: trio.abc.ReceiveChannel[bytes]):
        idx = 0
        async for line in stream:
            try:
                content = line.decode("utf-8").strip()
                result = callback(idx, content)
            except Exception:
                raise
            if result is not None:
                await self._send_channel.send(bool(result))
                break
            idx += 1

    def onexit(self, code: int) -> bool:
        return code == 0

    def onstdout(self, idx: int, line: str) -> bool | None:
        pass

    def onstderr(self, idx: int, line: str) -> bool | None:
        pass
