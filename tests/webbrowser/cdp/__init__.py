# TODO: trio>0.22 release: remove __future__ import (generic memorychannels)
from __future__ import annotations

from typing import List

import trio
from trio_websocket import CloseReason, ConnectionClosed  # type: ignore[import]


class FakeWebsocketConnection:
    sender: trio.MemorySendChannel[str]
    receiver: trio.MemoryReceiveChannel[str]

    def __init__(self) -> None:
        self.sender, self.receiver = trio.open_memory_channel(10)
        self.sent: List[str] = []
        self.closed: bool = False

    async def send_message(self, message: str):
        self.sent.append(message)

    async def get_message(self):
        try:
            return await self.receiver.receive()
        except BaseException:
            # noinspection PyTypeChecker
            raise ConnectionClosed(CloseReason(1000, None)) from None

    async def aclose(self):
        # sync
        self.sender.close()
        self.receiver.close()
        self.closed = True
