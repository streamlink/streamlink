# TODO: trio>0.22 release: remove __future__ import (generic memorychannels)
from __future__ import annotations

import dataclasses
import itertools
import json
import logging
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Generator, Generic, Optional, Set, Type, TypeVar, Union, cast

import trio
from trio_websocket import ConnectionClosed, WebSocketConnection, connect_websocket_url  # type: ignore[import]

from streamlink.logger import ALL
from streamlink.webbrowser.cdp.devtools.target import SessionID, TargetID, attach_to_target, create_target
from streamlink.webbrowser.cdp.devtools.util import T_JSON_DICT, parse_json_event
from streamlink.webbrowser.cdp.exceptions import CDPError


try:
    from typing import Self, TypeAlias  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover
    from typing_extensions import Self, TypeAlias


log = logging.getLogger(__name__)

MAX_BUFFER_SIZE = 10
MAX_MESSAGE_SIZE = 2 ** 24  # ~16MiB
CMD_TIMEOUT = 2

TCmdResponse = TypeVar("TCmdResponse")
TEvent = TypeVar("TEvent")
TEventChannels: TypeAlias = "Dict[Type[TEvent], Set[trio.MemorySendChannel[TEvent]]]"


class CDPEventListener(Generic[TEvent]):
    _sender: trio.MemorySendChannel[TEvent]
    _receiver: trio.MemoryReceiveChannel[TEvent]

    def __init__(self, event_channels: TEventChannels, event: Type[TEvent], max_buffer_size: int = MAX_BUFFER_SIZE):
        self._sender, self._receiver = trio.open_memory_channel(max_buffer_size)
        event_channels[event].add(self._sender)

    async def receive(self) -> TEvent:
        return await self._receiver.receive()

    def close(self) -> None:
        self._receiver.close()

    async def __aenter__(self) -> TEvent:
        return await self._receiver.receive()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        # sync
        self.close()

    def __aiter__(self) -> Self:
        return self

    async def __anext__(self) -> TEvent:
        try:
            return await self._receiver.receive()
        except trio.EndOfChannel as err:
            self.close()
            raise StopAsyncIteration from err

    def __del__(self) -> None:
        self.close()


@dataclasses.dataclass
class _CDPCmdBuffer(Generic[TCmdResponse]):
    cmd: Generator[dict, dict, TCmdResponse]
    response: Optional[Union[TCmdResponse, Exception]] = None
    event: trio.Event = dataclasses.field(default_factory=trio.Event)

    def set_response(self, response: Union[TCmdResponse, Exception]) -> None:
        self.response = response
        self.event.set()


# The design of CDPBase/CDPConnection/CDPSession is based on the trio-chrome-devtools-protocol project version 0.6.0
# https://github.com/HyperionGray/trio-chrome-devtools-protocol/blob/0.6.0/trio_cdp/__init__.py
#
# The MIT License (MIT)
#
# Copyright (c) 2018 Hyperion Gray
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


class CDPBase:
    def __init__(
        self,
        websocket: WebSocketConnection,
        target_id: Optional[TargetID] = None,
        session_id: Optional[SessionID] = None,
        cmd_timeout: float = CMD_TIMEOUT,
    ) -> None:
        self.websocket = websocket
        self.target_id = target_id
        self.session_id = session_id
        self.cmd_timeout = cmd_timeout
        self.event_channels: TEventChannels = defaultdict(set)
        self.cmd_buffers: Dict[int, _CDPCmdBuffer] = {}
        self.cmd_id = itertools.count()

    async def send(
        self,
        cmd: Generator[T_JSON_DICT, T_JSON_DICT, TCmdResponse],
        timeout: Optional[float] = None,
    ) -> TCmdResponse:
        cmd_id = next(self.cmd_id)
        cmd_buffer = _CDPCmdBuffer(cmd)

        self.cmd_buffers[cmd_id] = cmd_buffer

        cmd_data = next(cmd)
        cmd_data["id"] = cmd_id
        if self.session_id:
            cmd_data["sessionId"] = self.session_id

        message = json.dumps(cmd_data, separators=(",", ":"), sort_keys=True)
        log.log(ALL, f"Sending message: {message}")
        with trio.move_on_after(self.cmd_timeout if timeout is None else timeout) as cancel_scope:
            try:
                await self.websocket.send_message(message)
            except ConnectionClosed as err:
                self.cmd_buffers.pop(cmd_id, None)
                raise CDPError(err.reason) from err

            await cmd_buffer.event.wait()
        if cancel_scope.cancel_called:
            self.cmd_buffers.pop(cmd_id, None)
            raise CDPError("Sending CDP message and receiving its response timed out")

        response = cast(TCmdResponse, cmd_buffer.response)
        self.cmd_buffers.pop(cmd_id, None)

        if isinstance(response, Exception):
            raise response

        return response

    def listen(self, event: Type[TEvent], max_buffer_size: int = MAX_BUFFER_SIZE) -> CDPEventListener[TEvent]:
        return CDPEventListener(self.event_channels, event, max_buffer_size)

    def _handle_data(self, data: T_JSON_DICT) -> None:
        if "id" in data:
            self._handle_cmd_response(data)
        else:
            self._handle_event(data)

    def _handle_cmd_response(self, data: T_JSON_DICT) -> None:
        try:
            cmd_id: int = data["id"]
            cmd_buffer = self.cmd_buffers.pop(cmd_id)
        except KeyError:
            log.warning(f"Got a CDP command response with an unknown ID: {data['id']}")
            return

        if "error" in data:
            cmd_buffer.set_response(CDPError(f"Error in CDP command response {cmd_id}: {data['error']}"))
            return
        if "result" not in data:
            cmd_buffer.set_response(CDPError(f"No result in CDP command response {cmd_id}"))
            return

        cmd_result: T_JSON_DICT = data["result"]
        try:
            # send the response to the command's generator function (the first send() must stop the generator)
            cmd_buffer.cmd.send(cmd_result)
        except StopIteration as cm:
            # and on success, set the response result
            cmd_buffer.set_response(cm.value)
        except Exception as err:
            # handle any errors raised by the generator's result logic
            cmd_buffer.set_response(CDPError(f"Generator of CDP command ID {cmd_id} raised {type(err).__name__}: {err}"))
        else:
            cmd_buffer.set_response(CDPError(f"Generator of CDP command ID {cmd_id} did not exit when expected!"))

    def _handle_event(self, data: T_JSON_DICT) -> None:
        if "method" not in data or "params" not in data:
            log.warning("Invalid CDP event message received without method or params")
            return

        try:
            event = parse_json_event(data)
        except KeyError:
            log.warning(f"Unknown CDP event message received: {data['method']}")
            return

        log.log(ALL, f"Received event: {event!r}")
        broken_channels = set()
        for sender in self.event_channels[type(event)]:
            try:
                sender.send_nowait(event)
            except trio.WouldBlock:
                log.error(f"Unable to propagate CDP event {event!r} due to full channel")
            except trio.BrokenResourceError:
                broken_channels.add(sender)
                sender.close()
        self.event_channels[type(event)] -= broken_channels


class CDPConnection(CDPBase, trio.abc.AsyncResource):
    def __init__(self, websocket: WebSocketConnection, cmd_timeout: float) -> None:
        super().__init__(websocket=websocket, cmd_timeout=cmd_timeout)
        self.sessions: Dict[SessionID, CDPSession] = {}

    @classmethod
    @asynccontextmanager
    async def create(cls, url: str, timeout: Optional[float] = None) -> AsyncGenerator[Self, None]:
        async with trio.open_nursery() as nursery:
            websocket = await connect_websocket_url(nursery, url, max_message_size=MAX_MESSAGE_SIZE)
            cdp_connection = cls(websocket, timeout or CMD_TIMEOUT)
            nursery.start_soon(cdp_connection._task_reader)
            try:
                yield cdp_connection
            finally:
                await cdp_connection.aclose()

    async def aclose(self) -> None:
        await self.websocket.aclose()
        inst: CDPBase
        for inst in (self, *self.sessions.values()):
            for event_channels in inst.event_channels.values():
                for event_channel in event_channels:
                    event_channel.close()
            inst.event_channels.clear()
        self.sessions.clear()

    async def new_target(self, url: str = "") -> CDPSession:
        target_id = await self.send(create_target(url))

        return await self.get_session(target_id)

    async def get_session(self, target_id: TargetID) -> CDPSession:
        session_id = await self.send(attach_to_target(target_id, True))
        cdp_session = CDPSession(self.websocket, target_id=target_id, session_id=session_id, cmd_timeout=self.cmd_timeout)
        self.sessions[session_id] = cdp_session

        return cdp_session

    async def _task_reader(self) -> None:
        while True:
            try:
                message = await self.websocket.get_message()
            except ConnectionClosed:
                break

            try:
                data = json.loads(message)
            except json.JSONDecodeError as err:
                raise CDPError(f"Received invalid CDP JSON data: {err}") from err

            log.log(ALL, f"Received message: {message}")
            if "sessionId" not in data:
                self._handle_data(data)
            else:
                session_id = SessionID(data["sessionId"])
                if session_id not in self.sessions:
                    raise CDPError(f"Unknown CDP session ID: {session_id!r}")
                self.sessions[session_id]._handle_data(data)


class CDPSession(CDPBase):
    pass
