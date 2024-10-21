from __future__ import annotations

import contextlib
from collections.abc import Generator
from contextlib import nullcontext
from dataclasses import dataclass
from functools import partial
from unittest.mock import AsyncMock

import pytest
import trio
from trio.testing import MockClock, wait_all_tasks_blocked
from trio_websocket import CloseReason, ConnectionClosed, ConnectionTimeout  # type: ignore[import]

from streamlink.compat import ExceptionGroup
from streamlink.webbrowser.cdp.connection import MAX_BUFFER_SIZE, CDPConnection, CDPEventListener, CDPSession
from streamlink.webbrowser.cdp.devtools.target import SessionID, TargetID
from streamlink.webbrowser.cdp.devtools.util import T_JSON_DICT
from streamlink.webbrowser.cdp.exceptions import CDPError
from tests.webbrowser.cdp import FakeWebsocketConnection


EPSILON = 0.1


@dataclass
class FakeCommand(str):
    value: str

    def to_json(self) -> T_JSON_DICT:
        return {"value": self.value}

    @classmethod
    def from_json(cls, data: T_JSON_DICT):
        return cls(data["value"])


def fake_command(command: FakeCommand) -> Generator[T_JSON_DICT, T_JSON_DICT, FakeCommand]:
    json: T_JSON_DICT
    json = yield {"method": "Fake.fakeCommand", "params": command.to_json()}
    return FakeCommand.from_json(json)


def bad_command() -> Generator[T_JSON_DICT, T_JSON_DICT, None]:
    yield {"method": "Fake.badCommand", "params": {}}
    yield {}


@dataclass
class FakeEvent:
    value: str

    @classmethod
    def from_json(cls, data: T_JSON_DICT):
        return cls(data["value"])


@pytest.fixture()
async def cdp_connection(websocket_connection: FakeWebsocketConnection):
    try:
        async with CDPConnection.create("ws://localhost:1234/fake") as cdp_connection:
            assert isinstance(cdp_connection, CDPConnection)
            assert not websocket_connection.closed
            try:
                yield cdp_connection
            finally:
                await cdp_connection.aclose()
                assert cdp_connection.sessions == {}
    finally:
        assert websocket_connection.closed


class TestCreateConnection:
    @pytest.mark.trio()
    async def test_success(self, cdp_connection: CDPConnection):
        assert cdp_connection.target_id is None
        assert cdp_connection.session_id is None

    @pytest.mark.trio()
    async def test_failure(self, monkeypatch: pytest.MonkeyPatch):
        fake_connect_websocket_url = AsyncMock(side_effect=ConnectionTimeout)
        monkeypatch.setattr("streamlink.webbrowser.cdp.connection.connect_websocket_url", fake_connect_websocket_url)
        with pytest.raises(ExceptionGroup) as excinfo:
            async with CDPConnection.create("ws://localhost:1234/fake"):
                pass  # pragma: no cover
        assert excinfo.group_contains(ConnectionTimeout)

    @pytest.mark.trio()
    @pytest.mark.parametrize(
        ("timeout", "expected"),
        [
            pytest.param(None, 2, id="Default value of 2 seconds"),
            pytest.param(0, 2, id="No timeout uses default value"),
            pytest.param(3, 3, id="Custom timeout value"),
        ],
    )
    async def test_timeout(self, websocket_connection: FakeWebsocketConnection, timeout: int | None, expected: int):
        async with CDPConnection.create("ws://localhost:1234/fake", timeout=timeout) as cdp_conn:
            pass
        assert cdp_conn.cmd_timeout == expected


class TestReaderError:
    @pytest.mark.trio()
    async def test_invalid_json(self, caplog: pytest.LogCaptureFixture, websocket_connection: FakeWebsocketConnection):
        with pytest.raises(ExceptionGroup) as excinfo:  # noqa: PT012
            async with CDPConnection.create("ws://localhost:1234/fake"):
                assert not websocket_connection.closed
                await websocket_connection.sender.send("INVALID JSON")
                await wait_all_tasks_blocked()

        assert excinfo.group_contains(
            CDPError,
            match=r"^Received invalid CDP JSON data: Expecting value: line 1 column 1 \(char 0\)$",
        )
        assert caplog.records == []

    @pytest.mark.trio()
    async def test_unknown_session_id(self, caplog: pytest.LogCaptureFixture, websocket_connection: FakeWebsocketConnection):
        with pytest.raises(ExceptionGroup) as excinfo:  # noqa: PT012
            async with CDPConnection.create("ws://localhost:1234/fake"):
                assert not websocket_connection.closed
                await websocket_connection.sender.send("""{"sessionId":"unknown"}""")
                await wait_all_tasks_blocked()

        assert excinfo.group_contains(CDPError, match=r"^Unknown CDP session ID: SessionID\('unknown'\)$")
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            ("streamlink.webbrowser.cdp.connection", "all", """Received message: {"sessionId":"unknown"}"""),
        ]


@contextlib.contextmanager
def raises_group(*group_contains):
    try:
        with pytest.raises(ExceptionGroup) as excinfo:
            yield
    finally:
        for args, kwargs, expected in group_contains:
            assert excinfo.group_contains(*args, **kwargs) is expected


class TestSend:
    # noinspection PyUnusedLocal
    @pytest.mark.trio()
    @pytest.mark.parametrize(
        ("timeout", "jump", "raises"),
        [
            pytest.param(
                None,
                2 - EPSILON,
                nullcontext(),
                id="Default timeout, response in time",
            ),
            pytest.param(
                None,
                2,
                raises_group(
                    ((CDPError,), {"match": "^Sending CDP message and receiving its response timed out$"}, True),
                ),
                id="Default timeout, response not in time",
            ),
            pytest.param(
                3,
                3 - EPSILON,
                nullcontext(),
                id="Custom timeout, response in time",
            ),
            pytest.param(
                3,
                3,
                raises_group(
                    ((CDPError,), {"match": "^Sending CDP message and receiving its response timed out$"}, True),
                ),
                id="Custom timeout, response not in time",
            ),
        ],
    )
    async def test_timeout(
        self,
        cdp_connection: CDPConnection,
        websocket_connection: FakeWebsocketConnection,
        autojump_clock: MockClock,
        timeout: float | None,
        jump: float,
        raises: nullcontext,
    ):
        assert cdp_connection.cmd_timeout == 2
        assert cdp_connection.cmd_buffers == {}
        assert websocket_connection.sent == []

        async def response():
            await trio.sleep(jump)
            await websocket_connection.sender.send("""{"id":0,"result":{"value":"foo"}}""")

        with raises:
            async with trio.open_nursery() as nursery:
                nursery.start_soon(partial(cdp_connection.send, fake_command(FakeCommand("foo")), timeout=timeout))
                nursery.start_soon(response)

        assert cdp_connection.cmd_buffers == {}
        assert websocket_connection.sent == ["""{"id":0,"method":"Fake.fakeCommand","params":{"value":"foo"}}"""]

    @pytest.mark.trio()
    async def test_closed(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        cdp_connection: CDPConnection,
        websocket_connection: FakeWebsocketConnection,
    ):
        # noinspection PyTypeChecker
        fake_send_message = AsyncMock(side_effect=ConnectionClosed(CloseReason(1000, None)))
        monkeypatch.setattr(FakeWebsocketConnection, "send_message", fake_send_message)

        assert cdp_connection.cmd_buffers == {}
        assert websocket_connection.sent == []

        with pytest.raises(CDPError) as cm:
            await cdp_connection.send(fake_command(FakeCommand("foo")))

        assert str(cm.value) == "CloseReason<code=1000, name=NORMAL_CLOSURE, reason=None>"
        assert cdp_connection.cmd_buffers == {}
        assert websocket_connection.sent == []
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Sending message: {"id":0,"method":"Fake.fakeCommand","params":{"value":"foo"}}""",
            ),
        ]

    @pytest.mark.trio()
    async def test_bad_command(
        self,
        caplog: pytest.LogCaptureFixture,
        cdp_connection: CDPConnection,
        websocket_connection: FakeWebsocketConnection,
    ):
        assert cdp_connection.cmd_buffers == {}
        assert websocket_connection.sent == []

        with pytest.raises(ExceptionGroup) as excinfo:  # noqa: PT012
            async with trio.open_nursery() as nursery:
                nursery.start_soon(cdp_connection.send, bad_command())
                nursery.start_soon(websocket_connection.sender.send, """{"id":0,"result":{}}""")

        assert excinfo.group_contains(CDPError, match="^Generator of CDP command ID 0 did not exit when expected!$")
        assert cdp_connection.cmd_buffers == {}
        assert websocket_connection.sent == ["""{"id":0,"method":"Fake.badCommand","params":{}}"""]
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Sending message: {"id":0,"method":"Fake.badCommand","params":{}}""",
            ),
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Received message: {"id":0,"result":{}}""",
            ),
        ]

    @pytest.mark.trio()
    async def test_result_exception(
        self,
        caplog: pytest.LogCaptureFixture,
        cdp_connection: CDPConnection,
        websocket_connection: FakeWebsocketConnection,
    ):
        assert cdp_connection.cmd_buffers == {}
        assert websocket_connection.sent == []

        with pytest.raises(ExceptionGroup) as excinfo:  # noqa: PT012
            async with trio.open_nursery() as nursery:
                nursery.start_soon(cdp_connection.send, fake_command(FakeCommand("foo")))
                nursery.start_soon(websocket_connection.sender.send, """{"id":0,"result":{}}""")

        assert excinfo.group_contains(CDPError, match="^Generator of CDP command ID 0 raised KeyError: 'value'$")
        assert cdp_connection.cmd_buffers == {}
        assert websocket_connection.sent == ["""{"id":0,"method":"Fake.fakeCommand","params":{"value":"foo"}}"""]
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Sending message: {"id":0,"method":"Fake.fakeCommand","params":{"value":"foo"}}""",
            ),
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Received message: {"id":0,"result":{}}""",
            ),
        ]

    @pytest.mark.trio()
    async def test_result_success(
        self,
        caplog: pytest.LogCaptureFixture,
        cdp_connection: CDPConnection,
        websocket_connection: FakeWebsocketConnection,
    ):
        results = {}

        async def send(key):
            results[key] = await cdp_connection.send(fake_command(FakeCommand(key)))

        assert cdp_connection.cmd_buffers == {}
        assert websocket_connection.sent == []

        async with trio.open_nursery() as nursery:
            # ensure that we start the tasks in the correct order
            nursery.start_soon(send, "foo")
            await wait_all_tasks_blocked()
            nursery.start_soon(send, "bar")
            await wait_all_tasks_blocked()

            assert list(cdp_connection.cmd_buffers.keys()) == [0, 1]
            assert all(buf.response is None for buf in cdp_connection.cmd_buffers.values())
            assert all(buf.event.is_set() is False for buf in cdp_connection.cmd_buffers.values())

            # send result of second command first
            nursery.start_soon(websocket_connection.sender.send, """{"id":1,"result":{"value":"BAR"}}""")
            await wait_all_tasks_blocked()
            nursery.start_soon(websocket_connection.sender.send, """{"id":0,"result":{"value":"FOO"}}""")

        assert list(results.keys()) == ["bar", "foo"]
        assert all(isinstance(result, FakeCommand) for result in results.values())
        assert results["foo"].value == "FOO"
        assert results["bar"].value == "BAR"

        assert cdp_connection.cmd_buffers == {}
        assert websocket_connection.sent == [
            """{"id":0,"method":"Fake.fakeCommand","params":{"value":"foo"}}""",
            """{"id":1,"method":"Fake.fakeCommand","params":{"value":"bar"}}""",
        ]
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Sending message: {"id":0,"method":"Fake.fakeCommand","params":{"value":"foo"}}""",
            ),
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Sending message: {"id":1,"method":"Fake.fakeCommand","params":{"value":"bar"}}""",
            ),
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Received message: {"id":1,"result":{"value":"BAR"}}""",
            ),
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Received message: {"id":0,"result":{"value":"FOO"}}""",
            ),
        ]


class TestHandleCmdResponse:
    @pytest.mark.trio()
    async def test_unknown_id(
        self,
        caplog: pytest.LogCaptureFixture,
        cdp_connection: CDPConnection,
        websocket_connection: FakeWebsocketConnection,
    ):
        assert cdp_connection.cmd_buffers == {}

        await websocket_connection.sender.send("""{"id":123}""")
        await wait_all_tasks_blocked()

        assert cdp_connection.cmd_buffers == {}
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Received message: {"id":123}""",
            ),
            (
                "streamlink.webbrowser.cdp.connection",
                "warning",
                "Got a CDP command response with an unknown ID: 123",
            ),
        ]

    @pytest.mark.trio()
    async def test_response_error(
        self,
        caplog: pytest.LogCaptureFixture,
        cdp_connection: CDPConnection,
        websocket_connection: FakeWebsocketConnection,
    ):
        assert cdp_connection.cmd_buffers == {}
        assert websocket_connection.sent == []

        with pytest.raises(ExceptionGroup) as excinfo:  # noqa: PT012
            async with trio.open_nursery() as nursery:
                nursery.start_soon(cdp_connection.send, fake_command(FakeCommand("foo")))
                nursery.start_soon(websocket_connection.sender.send, """{"id":0,"error":"Some error message"}""")

        assert excinfo.group_contains(CDPError, match="^Error in CDP command response 0: Some error message$")
        assert cdp_connection.cmd_buffers == {}
        assert websocket_connection.sent == ["""{"id":0,"method":"Fake.fakeCommand","params":{"value":"foo"}}"""]
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Sending message: {"id":0,"method":"Fake.fakeCommand","params":{"value":"foo"}}""",
            ),
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Received message: {"id":0,"error":"Some error message"}""",
            ),
        ]

    @pytest.mark.trio()
    async def test_response_no_result(
        self,
        caplog: pytest.LogCaptureFixture,
        cdp_connection: CDPConnection,
        websocket_connection: FakeWebsocketConnection,
    ):
        assert cdp_connection.cmd_buffers == {}
        assert websocket_connection.sent == []

        with pytest.raises(ExceptionGroup) as excinfo:  # noqa: PT012
            async with trio.open_nursery() as nursery:
                nursery.start_soon(cdp_connection.send, fake_command(FakeCommand("foo")))
                nursery.start_soon(websocket_connection.sender.send, """{"id":0}""")

        assert excinfo.group_contains(CDPError, match="^No result in CDP command response 0$")
        assert cdp_connection.cmd_buffers == {}
        assert websocket_connection.sent == ["""{"id":0,"method":"Fake.fakeCommand","params":{"value":"foo"}}"""]
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Sending message: {"id":0,"method":"Fake.fakeCommand","params":{"value":"foo"}}""",
            ),
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Received message: {"id":0}""",
            ),
        ]


class TestSession:
    @pytest.fixture()
    async def cdp_session(self, cdp_connection: CDPConnection):
        target_id = TargetID("01234")
        session_id = SessionID("56789")
        session = cdp_connection.sessions[session_id] = CDPSession(
            cdp_connection.websocket,
            target_id=target_id,
            session_id=session_id,
            cmd_timeout=cdp_connection.cmd_timeout,
        )
        return session

    @pytest.mark.trio()
    async def test_new_target(
        self,
        caplog: pytest.LogCaptureFixture,
        cdp_connection: CDPConnection,
        websocket_connection: FakeWebsocketConnection,
    ):
        assert cdp_connection.sessions == {}
        assert cdp_connection.cmd_buffers == {}
        assert websocket_connection.sent == []

        session = None

        async def send():
            nonlocal session
            session = await cdp_connection.new_target("http://localhost")

        async with trio.open_nursery() as nursery:
            nursery.start_soon(send)
            await wait_all_tasks_blocked()
            nursery.start_soon(websocket_connection.sender.send, """{"id":0,"result":{"targetId":"01234"}}""")
            await wait_all_tasks_blocked()
            nursery.start_soon(websocket_connection.sender.send, """{"id":1,"result":{"sessionId":"56789"}}""")

        assert isinstance(session, CDPSession)
        assert session.target_id == TargetID("01234")
        assert session.session_id == SessionID("56789")
        assert cdp_connection.sessions[SessionID("56789")] is session

        assert cdp_connection.cmd_buffers == {}
        assert websocket_connection.sent == [
            """{"id":0,"method":"Target.createTarget","params":{"url":"http://localhost"}}""",
            """{"id":1,"method":"Target.attachToTarget","params":{"flatten":true,"targetId":"01234"}}""",
        ]
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Sending message: {"id":0,"method":"Target.createTarget","params":{"url":"http://localhost"}}""",
            ),
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Received message: {"id":0,"result":{"targetId":"01234"}}""",
            ),
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Sending message: {"id":1,"method":"Target.attachToTarget","params":{"flatten":true,"targetId":"01234"}}""",
            ),
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Received message: {"id":1,"result":{"sessionId":"56789"}}""",
            ),
        ]

    @pytest.mark.trio()
    async def test_session_command(
        self,
        caplog: pytest.LogCaptureFixture,
        cdp_connection: CDPConnection,
        cdp_session: CDPSession,
        websocket_connection: FakeWebsocketConnection,
    ):
        results = {}

        async def send(obj, key):
            results[key] = await obj.send(fake_command(FakeCommand(key)))

        assert cdp_connection.cmd_buffers == {}
        assert cdp_session.cmd_buffers == {}
        assert websocket_connection.sent == []

        async with trio.open_nursery() as nursery:
            # ensure that we start the tasks in the correct order
            nursery.start_soon(send, cdp_connection, "foo")
            await wait_all_tasks_blocked()
            nursery.start_soon(send, cdp_session, "bar")
            await wait_all_tasks_blocked()

            assert list(cdp_connection.cmd_buffers.keys()) == [0]
            assert list(cdp_session.cmd_buffers.keys()) == [0]

            # send result of second command first
            nursery.start_soon(websocket_connection.sender.send, """{"id":0,"result":{"value":"BAR"},"sessionId":"56789"}""")
            await wait_all_tasks_blocked()
            nursery.start_soon(websocket_connection.sender.send, """{"id":0,"result":{"value":"FOO"}}""")

        assert list(results.keys()) == ["bar", "foo"]
        assert all(isinstance(result, FakeCommand) for result in results.values())
        assert results["foo"].value == "FOO"
        assert results["bar"].value == "BAR"

        assert cdp_connection.cmd_buffers == {}
        assert cdp_session.cmd_buffers == {}
        assert websocket_connection.sent == [
            """{"id":0,"method":"Fake.fakeCommand","params":{"value":"foo"}}""",
            """{"id":0,"method":"Fake.fakeCommand","params":{"value":"bar"},"sessionId":"56789"}""",
        ]
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Sending message: {"id":0,"method":"Fake.fakeCommand","params":{"value":"foo"}}""",
            ),
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Sending message: {"id":0,"method":"Fake.fakeCommand","params":{"value":"bar"},"sessionId":"56789"}""",
            ),
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Received message: {"id":0,"result":{"value":"BAR"},"sessionId":"56789"}""",
            ),
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Received message: {"id":0,"result":{"value":"FOO"}}""",
            ),
        ]


class TestHandleEvent:
    @pytest.fixture(autouse=True)
    def event_parsers(self, monkeypatch: pytest.MonkeyPatch):
        event_parsers: dict[str, type] = {
            "Fake.fakeEvent": FakeEvent,
        }
        monkeypatch.setattr("streamlink.webbrowser.cdp.devtools.util._event_parsers", event_parsers)
        return event_parsers

    @pytest.mark.trio()
    @pytest.mark.parametrize(
        "message",
        [
            pytest.param("""{"foo":"bar"}""", id="Missing method and params"),
            pytest.param("""{"method":"method"}""", id="Missing params"),
            pytest.param("""{"params":{}}""", id="Missing method"),
        ],
    )
    async def test_invalid_event(
        self,
        caplog: pytest.LogCaptureFixture,
        cdp_connection: CDPConnection,
        websocket_connection: FakeWebsocketConnection,
        message: str,
    ):
        await websocket_connection.sender.send(message)
        await wait_all_tasks_blocked()
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                f"Received message: {message}",
            ),
            (
                "streamlink.webbrowser.cdp.connection",
                "warning",
                "Invalid CDP event message received without method or params",
            ),
        ]

    @pytest.mark.trio()
    async def test_unknown_event(
        self,
        caplog: pytest.LogCaptureFixture,
        cdp_connection: CDPConnection,
        websocket_connection: FakeWebsocketConnection,
    ):
        await websocket_connection.sender.send("""{"method":"unknown","params":{}}""")
        await wait_all_tasks_blocked()
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Received message: {"method":"unknown","params":{}}""",
            ),
            (
                "streamlink.webbrowser.cdp.connection",
                "warning",
                "Unknown CDP event message received: unknown",
            ),
        ]

    @pytest.mark.trio()
    async def test_eventlistener(
        self,
        caplog: pytest.LogCaptureFixture,
        cdp_connection: CDPConnection,
        websocket_connection: FakeWebsocketConnection,
    ):
        assert FakeEvent not in cdp_connection.event_channels
        listener1 = cdp_connection.listen(FakeEvent)
        listener2 = cdp_connection.listen(FakeEvent)
        listener3 = cdp_connection.listen(FakeEvent, max_buffer_size=MAX_BUFFER_SIZE * 2)
        listeners = listener1, listener2, listener3
        assert FakeEvent in cdp_connection.event_channels
        assert len(cdp_connection.event_channels[FakeEvent]) == 3

        assert listener1._sender.statistics().max_buffer_size == MAX_BUFFER_SIZE
        assert listener2._sender.statistics().max_buffer_size == MAX_BUFFER_SIZE
        assert listener3._sender.statistics().max_buffer_size == MAX_BUFFER_SIZE * 2

        results = []

        async def listen_once(listener: CDPEventListener):
            async with listener as result:
                results.append(result)

        async def listen_twice(listener: CDPEventListener):
            async with listener as result:
                results.append(result)
                results.append(await listener.receive())

        async def listen_forever(listener: CDPEventListener):
            async for result in listener:
                results.append(result)

        async with trio.open_nursery() as nursery:
            nursery.start_soon(listen_once, listener1)
            await wait_all_tasks_blocked()
            nursery.start_soon(listen_twice, listener2)
            await wait_all_tasks_blocked()
            nursery.start_soon(listen_forever, listener3)
            await wait_all_tasks_blocked()

            await websocket_connection.sender.send("""{"method":"Fake.fakeEvent","params":{"value":"foo"}}""")
            await wait_all_tasks_blocked()
            assert len(cdp_connection.event_channels[FakeEvent]) == 3

            await websocket_connection.sender.send("""{"method":"Fake.fakeEvent","params":{"value":"bar"}}""")
            await wait_all_tasks_blocked()
            assert len(cdp_connection.event_channels[FakeEvent]) == 2

            await websocket_connection.sender.send("""{"method":"Fake.fakeEvent","params":{"value":"baz"}}""")
            await wait_all_tasks_blocked()
            assert len(cdp_connection.event_channels[FakeEvent]) == 1

            await cdp_connection.aclose()

        assert results == [
            FakeEvent(value="foo"),
            FakeEvent(value="foo"),
            FakeEvent(value="foo"),
            FakeEvent(value="bar"),
            FakeEvent(value="bar"),
            FakeEvent(value="baz"),
        ]
        assert FakeEvent not in cdp_connection.event_channels
        assert all(listener._sender._closed for listener in listeners)  # type: ignore[attr-defined]
        assert all(listener._receiver._closed for listener in listeners)  # type: ignore[attr-defined]
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Received message: {"method":"Fake.fakeEvent","params":{"value":"foo"}}""",
            ),
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                "Received event: FakeEvent(value='foo')",
            ),
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Received message: {"method":"Fake.fakeEvent","params":{"value":"bar"}}""",
            ),
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                "Received event: FakeEvent(value='bar')",
            ),
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Received message: {"method":"Fake.fakeEvent","params":{"value":"baz"}}""",
            ),
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                "Received event: FakeEvent(value='baz')",
            ),
        ]

    @pytest.mark.trio()
    async def test_would_block(
        self,
        caplog: pytest.LogCaptureFixture,
        cdp_connection: CDPConnection,
        websocket_connection: FakeWebsocketConnection,
    ):
        assert FakeEvent not in cdp_connection.event_channels
        listener = cdp_connection.listen(FakeEvent, max_buffer_size=1)
        assert FakeEvent in cdp_connection.event_channels
        assert len(cdp_connection.event_channels[FakeEvent]) == 1

        assert listener._sender.statistics().current_buffer_used == 0
        assert listener._sender.statistics().max_buffer_size == 1

        await websocket_connection.sender.send("""{"method":"Fake.fakeEvent","params":{"value":"foo"}}""")
        await wait_all_tasks_blocked()
        assert listener._sender.statistics().current_buffer_used == 1
        assert listener._sender.statistics().max_buffer_size == 1

        await websocket_connection.sender.send("""{"method":"Fake.fakeEvent","params":{"value":"bar"}}""")
        await wait_all_tasks_blocked()
        assert listener._sender.statistics().current_buffer_used == 1
        assert listener._sender.statistics().max_buffer_size == 1

        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Received message: {"method":"Fake.fakeEvent","params":{"value":"foo"}}""",
            ),
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                "Received event: FakeEvent(value='foo')",
            ),
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                """Received message: {"method":"Fake.fakeEvent","params":{"value":"bar"}}""",
            ),
            (
                "streamlink.webbrowser.cdp.connection",
                "all",
                "Received event: FakeEvent(value='bar')",
            ),
            (
                "streamlink.webbrowser.cdp.connection",
                "error",
                """Unable to propagate CDP event FakeEvent(value='bar') due to full channel""",
            ),
        ]
