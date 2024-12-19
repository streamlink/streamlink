from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextlib import nullcontext
from typing import TYPE_CHECKING, cast
from unittest.mock import ANY, AsyncMock, Mock, call

import pytest
import trio
from trio.testing import wait_all_tasks_blocked

from streamlink.compat import ExceptionGroup
from streamlink.session import Streamlink
from streamlink.webbrowser.cdp.client import CDPClient, CDPClientSession, RequestPausedHandler
from streamlink.webbrowser.cdp.connection import CDPConnection, CDPSession
from streamlink.webbrowser.cdp.devtools.fetch import RequestPaused
from streamlink.webbrowser.cdp.devtools.target import SessionID, TargetID
from streamlink.webbrowser.cdp.exceptions import CDPError
from tests.webbrowser.cdp import FakeWebsocketConnection


if TYPE_CHECKING:
    from typing_extensions import TypeAlias


TAsyncHandler: TypeAlias = "AsyncMock | Callable[[CDPClientSession, RequestPaused], Awaitable]"


def async_handler(*args, **kwargs):
    return cast(TAsyncHandler, AsyncMock(*args, **kwargs))


@pytest.fixture()
def chromium_webbrowser(monkeypatch: pytest.MonkeyPatch):
    # noinspection PyUnusedLocal
    def mock_launch(*args, **kwargs):
        return trio.open_nursery()

    mock_chromium_webbrowser = Mock(
        launch=Mock(side_effect=mock_launch),
        get_websocket_url=Mock(return_value="ws://localhost:1234/fake"),
    )
    mock_chromium_webbrowser_class = Mock(return_value=mock_chromium_webbrowser)
    monkeypatch.setattr("streamlink.webbrowser.cdp.client.ChromiumWebbrowser", mock_chromium_webbrowser_class)
    return mock_chromium_webbrowser


@pytest.fixture()
async def cdp_client(
    request: pytest.FixtureRequest,
    session: Streamlink,
    chromium_webbrowser: Mock,
    websocket_connection: FakeWebsocketConnection,
):
    params = getattr(request, "param", {})
    headless = params.get("headless", False)
    async with CDPClient.run(session, headless=headless) as cdp_client:
        yield cdp_client


@pytest.fixture()
def cdp_client_session(request: pytest.FixtureRequest, cdp_client: CDPClient):
    target_id = TargetID("01234")
    session_id = SessionID("56789")
    session = cdp_client.cdp_connection.sessions[session_id] = CDPSession(
        cdp_client.cdp_connection.websocket,
        target_id=target_id,
        session_id=session_id,
        cmd_timeout=cdp_client.cdp_connection.cmd_timeout,
    )
    fail_unhandled_requests = getattr(request, "param", False)
    return CDPClientSession(cdp_client, session, fail_unhandled_requests)


class TestLaunch:
    @pytest.fixture()
    def cdp_client(self):
        return Mock()

    @pytest.fixture(autouse=True)
    def mock_run(self, monkeypatch: pytest.MonkeyPatch, cdp_client: Mock):
        mock_run = Mock(
            return_value=Mock(
                __aenter__=AsyncMock(return_value=cdp_client),
                __aexit__=AsyncMock(),
            ),
        )
        monkeypatch.setattr(CDPClient, "run", mock_run)
        return mock_run

    @pytest.fixture(autouse=True)
    def _mock_launch(self, request: pytest.FixtureRequest, session: Streamlink, mock_run, cdp_client: Mock):
        result = object()
        mock_runner = AsyncMock(return_value=result)
        with getattr(request, "param", nullcontext()):
            assert CDPClient.launch(session, mock_runner) is result
            assert mock_runner.await_args_list == [call(cdp_client)]

    @pytest.mark.parametrize(
        ("session", "options"),
        [
            pytest.param(
                {},
                dict(executable=None, timeout=20.0, cdp_host=None, cdp_port=None, cdp_timeout=2.0, headless=False),
                id="Default options",
            ),
            pytest.param(
                {
                    "webbrowser-executable": "foo",
                    "webbrowser-timeout": 123.45,
                    "webbrowser-cdp-host": "::1",
                    "webbrowser-cdp-port": 1234,
                    "webbrowser-cdp-timeout": 12.34,
                    "webbrowser-headless": True,
                },
                dict(executable="foo", timeout=123.45, cdp_host="::1", cdp_port=1234, cdp_timeout=12.34, headless=True),
                id="Custom options",
            ),
        ],
        indirect=["session"],
    )
    def test_options(self, session: Streamlink, mock_run: Mock, options: dict):
        assert mock_run.call_args_list == [call(session=session, **options)]

    # noinspection PyTestParametrized
    @pytest.mark.usefixtures("_mock_launch")
    @pytest.mark.parametrize(
        ("session", "_mock_launch"),
        [
            pytest.param(
                {"webbrowser": False},
                pytest.raises(CDPError, match=r"^The webbrowser API has been disabled by the user$"),
                id="Raises CDPError",
            ),
        ],
        indirect=["session", "_mock_launch"],
    )
    def test_disabled(self, session: Streamlink, mock_run):
        assert not mock_run.called


class TestRun:
    @pytest.mark.trio()
    async def test_no_session(
        self,
        session: Streamlink,
        chromium_webbrowser: Mock,
        cdp_client: CDPClient,
        websocket_connection: FakeWebsocketConnection,
    ):
        assert isinstance(cdp_client, CDPClient)
        assert isinstance(cdp_client.cdp_connection, CDPConnection)
        assert isinstance(cdp_client.nursery, trio.Nursery)
        assert chromium_webbrowser.launch.called
        assert chromium_webbrowser.get_websocket_url.call_args_list == [call(session)]
        assert websocket_connection.sent == []

    @pytest.mark.trio()
    @pytest.mark.parametrize("fail_unhandled_requests", [False, True])
    async def test_session(
        self,
        cdp_client: CDPClient,
        websocket_connection: FakeWebsocketConnection,
        fail_unhandled_requests,
    ):
        client_session = None

        async def new_session():
            nonlocal client_session
            async with cdp_client.session(fail_unhandled_requests=fail_unhandled_requests) as client_session:
                pass

        async with trio.open_nursery() as nursery:
            nursery.start_soon(new_session)
            await wait_all_tasks_blocked()
            nursery.start_soon(websocket_connection.sender.send, """{"id":0,"result":{"targetId":"01234"}}""")
            await wait_all_tasks_blocked()
            nursery.start_soon(websocket_connection.sender.send, """{"id":1,"result":{"sessionId":"56789"}}""")

        assert isinstance(client_session, CDPClientSession)
        assert isinstance(client_session.cdp_session, CDPSession)
        assert client_session._fail_unhandled == fail_unhandled_requests
        assert websocket_connection.sent == [
            """{"id":0,"method":"Target.createTarget","params":{"url":""}}""",
            """{"id":1,"method":"Target.attachToTarget","params":{"flatten":true,"targetId":"01234"}}""",
        ]


class TestEvaluate:
    @pytest.mark.trio()
    async def test_success(self, cdp_client_session: CDPClientSession, websocket_connection: FakeWebsocketConnection):
        result = None

        async def evaluate():
            nonlocal result
            result = await cdp_client_session.evaluate("new Promise(r=>r('foo'))")

        async with trio.open_nursery() as nursery:
            nursery.start_soon(evaluate)
            await wait_all_tasks_blocked()
            await websocket_connection.sender.send(
                """{"id":0,"sessionId":"56789","result":{"result":{"type":"string","value":"foo"}}}""",
            )

        assert result == "foo"

    @pytest.mark.trio()
    async def test_exception(self, cdp_client_session: CDPClientSession, websocket_connection: FakeWebsocketConnection):
        with pytest.raises(ExceptionGroup) as excinfo:  # noqa: PT012
            async with trio.open_nursery() as nursery:
                nursery.start_soon(cdp_client_session.evaluate, "/")

                await wait_all_tasks_blocked()
                # language=json
                await websocket_connection.sender.send("""
                    {"id":0, "sessionId":"56789", "result": {
                        "result": {"type": "object", "subclass": "error"},
                        "exceptionDetails": {
                            "exceptionId": 1,
                            "text": "Uncaught",
                            "lineNumber": 0,
                            "columnNumber": 0,
                            "exception": {
                                "type": "object",
                                "subtype": "error",
                                "className": "SyntaxError",
                                "description": "SyntaxError: Invalid regular expression: missing /"
                            }
                        }
                    }}
                """)

        assert excinfo.group_contains(CDPError, match="^SyntaxError: Invalid regular expression: missing /$")

    @pytest.mark.trio()
    async def test_error(self, cdp_client_session: CDPClientSession, websocket_connection: FakeWebsocketConnection):
        with pytest.raises(ExceptionGroup) as excinfo:  # noqa: PT012
            async with trio.open_nursery() as nursery:
                nursery.start_soon(cdp_client_session.evaluate, "new Error('foo')")

                await wait_all_tasks_blocked()
                # language=json
                await websocket_connection.sender.send("""
                    {"id":0, "sessionId":"56789", "result": {
                        "result": {
                            "type": "object",
                            "subtype": "error",
                            "className": "Error",
                            "description": "Error: foo\\n    at <anonymous>:1:1"
                        }
                    }}
                """)

        assert excinfo.group_contains(CDPError, match="^Error: foo\\n    at <anonymous>:1:1$")


class TestRequestPausedHandler:
    @pytest.mark.parametrize(
        ("url_pattern", "regex_pattern"),
        [
            pytest.param(
                r"abc?def?xyz",
                r"^abc.def.xyz$",
                id="Question mark",
            ),
            pytest.param(
                r"abc*def*xyz",
                r"^abc.+def.+xyz$",
                id="Star",
            ),
            pytest.param(
                r"^(.[a-z])\d$",
                r"^\^\(\.\[a\-z\]\)\\d\$$",
                id="Special characters",
            ),
            pytest.param(
                r"abc\?def\*xyz",
                r"^abc\?def\*xyz$",
                id="Escaped question mark and star",
            ),
            pytest.param(
                r"abc\\?def\\*xyz",
                r"^abc\\\\.def\\\\.+xyz$",
                id="2 escape characters",
            ),
            pytest.param(
                r"abc\\\?def\\\*xyz",
                r"^abc\\\\\?def\\\\\*xyz$",
                id="3 escape characters",
            ),
            pytest.param(
                r"abc\\\\?def\\\\*xyz",
                r"^abc\\\\\\\\.def\\\\\\\\.+xyz$",
                id="4 escape characters",
            ),
            pytest.param(
                r"abc\\\\\?def\\\\\*xyz",
                r"^abc\\\\\\\\\?def\\\\\\\\\*xyz$",
                id="5 escape characters",
            ),
            pytest.param(
                r"http://*.name.tld/foo\?bar=baz",
                r"^http://.+\.name\.tld/foo\?bar=baz$",
                id="Typical URL pattern",
            ),
        ],
    )
    def test_url_pattern_to_regex_pattern(self, url_pattern: str, regex_pattern: str):
        assert RequestPausedHandler._url_pattern_to_regex_pattern(url_pattern).pattern == regex_pattern

    @pytest.mark.trio()
    async def test_client_registration(self, cdp_client_session: CDPClientSession):
        assert len(cdp_client_session._request_handlers) == 0
        cdp_client_session.add_request_handler(async_handler())
        cdp_client_session.add_request_handler(async_handler(), on_request=True)
        cdp_client_session.add_request_handler(async_handler(), url_pattern="foo")
        cdp_client_session.add_request_handler(async_handler(), url_pattern="foo", on_request=True)
        assert len(cdp_client_session._request_handlers) == 4
        assert all(request_handler.async_handler for request_handler in cdp_client_session._request_handlers)
        assert all(request_handler.url_pattern == "*" for request_handler in cdp_client_session._request_handlers[:2])
        assert all(request_handler.url_pattern == "foo" for request_handler in cdp_client_session._request_handlers[2:])
        assert not cdp_client_session._request_handlers[0].on_request
        assert not cdp_client_session._request_handlers[2].on_request
        assert cdp_client_session._request_handlers[1].on_request
        assert cdp_client_session._request_handlers[3].on_request

    @pytest.mark.parametrize(
        ("args", "matches"),
        [
            pytest.param(
                dict(async_handler=async_handler(), on_request=False),
                False,
                id="On response - Any URL",
            ),
            pytest.param(
                dict(async_handler=async_handler(), on_request=True),
                True,
                id="On request - Any URL",
            ),
            pytest.param(
                dict(async_handler=async_handler(), url_pattern="http://localhost/", on_request=True),
                True,
                id="Matching URL",
            ),
            pytest.param(
                dict(async_handler=async_handler(), url_pattern="http://l?c?l*/", on_request=True),
                True,
                id="Matching wildcard URL",
            ),
            pytest.param(
                dict(async_handler=async_handler(), url_pattern="http://other/", on_request=True),
                False,
                id="Non-matching URL",
            ),
        ],
    )
    def test_matches_request(self, args: dict, matches: bool):
        request = RequestPaused.from_json({
            "requestId": "request-1",
            "frameId": "frame-1",
            "request": {
                "url": "http://localhost/",
                "method": "GET",
                "headers": {},
                "initialPriority": "VeryHigh",
                "referrerPolicy": "strict-origin-when-cross-origin",
            },
            "resourceType": "Document",
        })
        request_handler = RequestPausedHandler(**args)
        assert request_handler.matches(request) is matches

    @pytest.mark.parametrize(
        ("args", "matches"),
        [
            pytest.param(
                dict(async_handler=async_handler(), on_request=False),
                True,
                id="On response - Any URL",
            ),
            pytest.param(
                dict(async_handler=async_handler(), on_request=True),
                False,
                id="On request - Any URL",
            ),
            pytest.param(
                dict(async_handler=async_handler(), url_pattern="http://localhost/", on_request=False),
                True,
                id="Matching URL",
            ),
            pytest.param(
                dict(async_handler=async_handler(), url_pattern="http://l?c?l*/", on_request=False),
                True,
                id="Matching wildcard URL",
            ),
            pytest.param(
                dict(async_handler=async_handler(), url_pattern="http://other/", on_request=False),
                False,
                id="Non-matching URL",
            ),
        ],
    )
    def test_matches_response(self, args: dict, matches: bool):
        request = RequestPaused.from_json({
            "requestId": "request-1",
            "frameId": "frame-1",
            "request": {
                "url": "http://localhost/",
                "method": "GET",
                "headers": {},
                "initialPriority": "VeryHigh",
                "referrerPolicy": "strict-origin-when-cross-origin",
            },
            "resourceType": "Document",
            "responseStatusCode": 200,
        })
        request_handler = RequestPausedHandler(**args)
        assert request_handler.matches(request) is matches


class TestNavigate:
    @pytest.mark.trio()
    async def test_detach(self, cdp_client_session: CDPClientSession, websocket_connection: FakeWebsocketConnection):
        async def navigate():
            async with cdp_client_session.navigate("https://foo"):
                pass  # pragma: no cover

        with pytest.raises(ExceptionGroup) as excinfo:  # noqa: PT012
            async with trio.open_nursery() as nursery:
                nursery.start_soon(navigate)

                await wait_all_tasks_blocked()
                await websocket_connection.sender.send(
                    """{"method":"Target.detachedFromTarget","params":{"sessionId":"unknown"}}""",
                )
                await wait_all_tasks_blocked()
                await websocket_connection.sender.send(
                    """{"method":"Target.detachedFromTarget","params":{"sessionId":"56789"}}""",
                )

        assert excinfo.group_contains(CDPError, match="^Target has been detached$")

    @pytest.mark.trio()
    async def test_error(self, cdp_client_session: CDPClientSession, websocket_connection: FakeWebsocketConnection):
        async def navigate():
            async with cdp_client_session.navigate("https://foo"):
                pass  # pragma: no cover

        with pytest.raises(ExceptionGroup) as excinfo:  # noqa: PT012
            async with trio.open_nursery() as nursery:
                nursery.start_soon(navigate)

                await wait_all_tasks_blocked()
                assert websocket_connection.sent == [
                    """{"id":0,"method":"Page.enable","sessionId":"56789"}""",
                ]

                await websocket_connection.sender.send(
                    """{"id":0,"result":{},"sessionId":"56789"}""",
                )
                await wait_all_tasks_blocked()
                assert websocket_connection.sent == [
                    """{"id":0,"method":"Page.enable","sessionId":"56789"}""",
                    """{"id":1,"method":"Page.navigate","params":{"url":"https://foo"},"sessionId":"56789"}""",
                ]

                await websocket_connection.sender.send(
                    """{"id":1,"result":{"frameId":"frame-id-1","errorText":"failure"},"sessionId":"56789"}""",
                )
                await wait_all_tasks_blocked()
                assert websocket_connection.sent == [
                    """{"id":0,"method":"Page.enable","sessionId":"56789"}""",
                    """{"id":1,"method":"Page.navigate","params":{"url":"https://foo"},"sessionId":"56789"}""",
                    """{"id":2,"method":"Page.disable","sessionId":"56789"}""",
                ]

                await websocket_connection.sender.send(
                    """{"id":2,"result":{},"sessionId":"56789"}""",
                )

        assert excinfo.group_contains(CDPError, match="^Navigation error: failure$")

    @pytest.mark.trio()
    @pytest.mark.parametrize("cdp_client", [pytest.param({"headless": True}, id="headless")], indirect=True)
    async def test_loaded(
        self,
        cdp_client_session: CDPClientSession,
        websocket_connection: FakeWebsocketConnection,
        nursery: trio.Nursery,
    ):
        loaded = False

        async def navigate():
            nonlocal loaded
            async with cdp_client_session.navigate("https://foo") as frame_id:
                assert frame_id == "frame-id-1"
                await cdp_client_session.loaded(frame_id)
                loaded = True

        nursery.start_soon(navigate)

        expected_commands_sent = [
            """{"id":0,"method":"Runtime.evaluate","params":"""
            + """{"awaitPromise":false,"expression":"navigator.userAgent"},"sessionId":"56789"}""",
            """{"id":1,"method":"Network.setUserAgentOverride","params":{"userAgent":"A Chrome UA"},"sessionId":"56789"}""",
            """{"id":2,"method":"Page.enable","sessionId":"56789"}""",
            """{"id":3,"method":"Page.navigate","params":{"url":"https://foo"},"sessionId":"56789"}""",
            """{"id":4,"method":"Page.disable","sessionId":"56789"}""",
        ]

        await wait_all_tasks_blocked()
        assert websocket_connection.sent == expected_commands_sent[0:1]
        await websocket_connection.sender.send(
            """{"id":0,"result":{"result":{"type":"string","value":"A HeadlessChrome UA"}},"sessionId":"56789"}""",
        )
        await wait_all_tasks_blocked()
        assert websocket_connection.sent == expected_commands_sent[0:2]
        await websocket_connection.sender.send(
            """{"id":1,"result":{},"sessionId":"56789"}""",
        )
        await wait_all_tasks_blocked()
        assert websocket_connection.sent == expected_commands_sent[0:3]
        await websocket_connection.sender.send(
            """{"id":2,"result":{},"sessionId":"56789"}""",
        )
        await wait_all_tasks_blocked()
        assert websocket_connection.sent == expected_commands_sent[0:4]
        await websocket_connection.sender.send(
            """{"id":3,"result":{"frameId":"frame-id-1"},"sessionId":"56789"}""",
        )
        await wait_all_tasks_blocked()
        await websocket_connection.sender.send(
            """{"method":"Page.frameStoppedLoading","params":{"frameId":"frame-id-unknown"},"sessionId":"56789"}""",
        )
        await wait_all_tasks_blocked()
        await websocket_connection.sender.send(
            """{"method":"Page.frameStoppedLoading","params":{"frameId":"frame-id-1"},"sessionId":"56789"}""",
        )
        await wait_all_tasks_blocked()
        assert websocket_connection.sent == expected_commands_sent[0:5]
        await websocket_connection.sender.send(
            """{"id":4,"result":{},"sessionId":"56789"}""",
        )

        assert loaded

    @pytest.mark.trio()
    @pytest.mark.parametrize(
        ("on_request", "fetch_enable_params"),
        [
            pytest.param(
                (False,),
                (
                    """{"handleAuthRequests":true,"patterns":[{"requestStage":"Response","urlPattern":"*"},"""
                    + """{"requestStage":"Response","urlPattern":"http://foo"}]}"""
                ),
                id="Single request handler, on response",
            ),
            pytest.param(
                (True,),
                (
                    """{"handleAuthRequests":true,"patterns":[{"requestStage":"Request","urlPattern":"*"},"""
                    + """{"requestStage":"Request","urlPattern":"http://foo"}]}"""
                ),
                id="Single request handler, on request",
            ),
            pytest.param(
                (False, False),
                (
                    """{"handleAuthRequests":true,"patterns":[{"requestStage":"Response","urlPattern":"*"},"""
                    + """{"requestStage":"Response","urlPattern":"http://foo"}]}"""
                ),
                id="Multiple request handlers, on response",
            ),
            pytest.param(
                (True, True),
                (
                    """{"handleAuthRequests":true,"patterns":[{"requestStage":"Request","urlPattern":"*"},"""
                    + """{"requestStage":"Request","urlPattern":"http://foo"}]}"""
                ),
                id="Multiple request handlers, on request",
            ),
            pytest.param(
                (False, True),
                (
                    """{"handleAuthRequests":true,"patterns":[{"requestStage":"Response","urlPattern":"*"},"""
                    + """{"requestStage":"Request","urlPattern":"*"},{"requestStage":"Response","urlPattern":"http://foo"},"""
                    + """{"requestStage":"Request","urlPattern":"http://foo"}]}"""
                ),
                id="Multiple request handlers, on response and on request",
            ),
            pytest.param(
                (True, False),
                (
                    """{"handleAuthRequests":true,"patterns":[{"requestStage":"Response","urlPattern":"*"},"""
                    + """{"requestStage":"Request","urlPattern":"*"},{"requestStage":"Response","urlPattern":"http://foo"},"""
                    + """{"requestStage":"Request","urlPattern":"http://foo"}]}"""
                ),
                id="Multiple request handlers, on request and on response",
            ),
        ],
    )
    async def test_fetch_enable(
        self,
        monkeypatch: pytest.MonkeyPatch,
        cdp_client_session: CDPClientSession,
        websocket_connection: FakeWebsocketConnection,
        nursery: trio.Nursery,
        on_request: tuple,
        fetch_enable_params: str,
    ):
        mock_on_fetch_request_paused = AsyncMock()
        monkeypatch.setattr(cdp_client_session, "_on_fetch_request_paused", mock_on_fetch_request_paused)

        for _on_request in on_request:
            cdp_client_session.add_request_handler(async_handler(), on_request=_on_request)
            cdp_client_session.add_request_handler(async_handler(), on_request=_on_request)
            cdp_client_session.add_request_handler(async_handler(), url_pattern="http://foo", on_request=_on_request)

        async def navigate():
            async with cdp_client_session.navigate("https://foo"):
                pass  # pragma: no cover

        assert not mock_on_fetch_request_paused.called

        nursery.start_soon(navigate)

        await wait_all_tasks_blocked()
        assert mock_on_fetch_request_paused.called
        assert websocket_connection.sent == [
            """{"id":0,"method":"Fetch.enable","params":""" + fetch_enable_params + ""","sessionId":"56789"}""",
        ]
        await websocket_connection.sender.send(
            """{"id":0,"result":{},"sessionId":"56789"}""",
        )

        await wait_all_tasks_blocked()
        assert websocket_connection.sent == [
            """{"id":0,"method":"Fetch.enable","params":""" + fetch_enable_params + ""","sessionId":"56789"}""",
            """{"id":1,"method":"Page.enable","sessionId":"56789"}""",
        ]
        await websocket_connection.sender.send(
            """{"id":1,"result":{},"sessionId":"56789"}""",
        )

        await wait_all_tasks_blocked()
        assert websocket_connection.sent == [
            """{"id":0,"method":"Fetch.enable","params":""" + fetch_enable_params + ""","sessionId":"56789"}""",
            """{"id":1,"method":"Page.enable","sessionId":"56789"}""",
            """{"id":2,"method":"Page.navigate","params":{"url":"https://foo"},"sessionId":"56789"}""",
        ]
        await websocket_connection.sender.send(
            """{"id":2,"result":{"frameId":"frame-id-1"},"sessionId":"56789"}""",
        )

        await wait_all_tasks_blocked()
        assert websocket_connection.sent == [
            """{"id":0,"method":"Fetch.enable","params":""" + fetch_enable_params + ""","sessionId":"56789"}""",
            """{"id":1,"method":"Page.enable","sessionId":"56789"}""",
            """{"id":2,"method":"Page.navigate","params":{"url":"https://foo"},"sessionId":"56789"}""",
            """{"id":3,"method":"Page.disable","sessionId":"56789"}""",
        ]
        await websocket_connection.sender.send(
            """{"id":3,"result":{},"sessionId":"56789"}""",
        )

        await wait_all_tasks_blocked()
        assert websocket_connection.sent == [
            """{"id":0,"method":"Fetch.enable","params":""" + fetch_enable_params + ""","sessionId":"56789"}""",
            """{"id":1,"method":"Page.enable","sessionId":"56789"}""",
            """{"id":2,"method":"Page.navigate","params":{"url":"https://foo"},"sessionId":"56789"}""",
            """{"id":3,"method":"Page.disable","sessionId":"56789"}""",
            """{"id":4,"method":"Fetch.disable","sessionId":"56789"}""",
        ]
        await websocket_connection.sender.send(
            """{"id":4,"result":{},"sessionId":"56789"}""",
        )


class TestRequestMethods:
    @pytest.fixture()
    def req_paused(self):
        return RequestPaused.from_json({
            "requestId": "request-1",
            "frameId": "frame-1",
            "request": {
                "url": "http://foo/",
                "method": "GET",
                "headers": {},
                "initialPriority": "VeryHigh",
                "referrerPolicy": "strict-origin-when-cross-origin",
            },
            "resourceType": "Document",
        })

    @pytest.mark.trio()
    async def test_continue_request(
        self,
        cdp_client_session: CDPClientSession,
        websocket_connection: FakeWebsocketConnection,
        req_paused: RequestPaused,
        nursery: trio.Nursery,
    ):
        nursery.start_soon(cdp_client_session.continue_request, req_paused, "http://bar", "POST", "data", {"a": "b", "c": "d"})

        await wait_all_tasks_blocked()
        assert "request-1" not in cdp_client_session._requests_handled
        assert websocket_connection.sent == [
            (
                """{"id":0,"method":"Fetch.continueRequest","params":"""
                + """{"headers":[{"name":"a","value":"b"},{"name":"c","value":"d"}],"method":"POST","""
                + """"postData":"ZGF0YQ==","requestId":"request-1","url":"http://bar"},"sessionId":"56789"}"""
            ),
        ]

        await websocket_connection.sender.send("""{"id":0,"result":{},"sessionId":"56789"}""")
        await wait_all_tasks_blocked()
        assert "request-1" in cdp_client_session._requests_handled

    @pytest.mark.trio()
    async def test_fail_request(
        self,
        cdp_client_session: CDPClientSession,
        websocket_connection: FakeWebsocketConnection,
        req_paused: RequestPaused,
        nursery: trio.Nursery,
    ):
        nursery.start_soon(cdp_client_session.fail_request, req_paused, "TimedOut")

        await wait_all_tasks_blocked()
        assert "request-1" not in cdp_client_session._requests_handled
        assert websocket_connection.sent == [
            (
                """{"id":0,"method":"Fetch.failRequest","params":"""
                + """{"errorReason":"TimedOut","requestId":"request-1"},"sessionId":"56789"}"""
            ),
        ]

        await websocket_connection.sender.send("""{"id":0,"result":{},"sessionId":"56789"}""")
        await wait_all_tasks_blocked()
        assert "request-1" in cdp_client_session._requests_handled

    @pytest.mark.trio()
    async def test_fulfill_request(
        self,
        cdp_client_session: CDPClientSession,
        websocket_connection: FakeWebsocketConnection,
        req_paused: RequestPaused,
        nursery: trio.Nursery,
    ):
        nursery.start_soon(cdp_client_session.fulfill_request, req_paused, 404, {"a": "b", "c": "d"}, "data")

        await wait_all_tasks_blocked()
        assert "request-1" not in cdp_client_session._requests_handled
        assert websocket_connection.sent == [
            (
                """{"id":0,"method":"Fetch.fulfillRequest","params":"""
                + """{"body":"ZGF0YQ==","requestId":"request-1","responseCode":404,"""
                + """"responseHeaders":[{"name":"a","value":"b"},{"name":"c","value":"d"}]},"sessionId":"56789"}"""
            ),
        ]

        await websocket_connection.sender.send("""{"id":0,"result":{},"sessionId":"56789"}""")
        await wait_all_tasks_blocked()
        assert "request-1" in cdp_client_session._requests_handled

    @pytest.mark.trio()
    async def test_alter_request(
        self,
        cdp_client_session: CDPClientSession,
        websocket_connection: FakeWebsocketConnection,
        req_paused: RequestPaused,
        nursery: trio.Nursery,
    ):
        async def alter_request():
            async with cdp_client_session.alter_request(req_paused, 404, {"a": "b", "c": "d"}) as cmproxy:
                assert cmproxy.body == ""
                cmproxy.body = "foo"

        nursery.start_soon(alter_request)

        await wait_all_tasks_blocked()
        assert "request-1" not in cdp_client_session._requests_handled
        assert websocket_connection.sent == [
            (
                """{"id":0,"method":"Fetch.fulfillRequest","params":"""
                + """{"body":"Zm9v","requestId":"request-1","responseCode":404,"""
                + """"responseHeaders":[{"name":"a","value":"b"},{"name":"c","value":"d"}]},"sessionId":"56789"}"""
            ),
        ]

        await websocket_connection.sender.send("""{"id":0,"result":{},"sessionId":"56789"}""")
        await wait_all_tasks_blocked()
        assert "request-1" in cdp_client_session._requests_handled

    @pytest.mark.trio()
    async def test_alter_request_response(
        self,
        cdp_client_session: CDPClientSession,
        websocket_connection: FakeWebsocketConnection,
        req_paused: RequestPaused,
        nursery: trio.Nursery,
    ):
        # turn the request into a response
        req_paused.response_status_code = 200

        async def alter_request():
            async with cdp_client_session.alter_request(req_paused, 404, {"a": "b", "c": "d"}) as cmproxy:
                assert cmproxy.body == "foo"
                assert cmproxy.response_code == 404
                assert cmproxy.response_headers == {"a": "b", "c": "d"}
                cmproxy.body = cmproxy.body.upper()
                cmproxy.response_code -= 3
                cmproxy.response_headers["c"] = "e"

        nursery.start_soon(alter_request)

        await wait_all_tasks_blocked()
        assert "request-1" not in cdp_client_session._requests_handled
        assert websocket_connection.sent == [
            """{"id":0,"method":"Fetch.getResponseBody","params":{"requestId":"request-1"},"sessionId":"56789"}""",
        ]

        await websocket_connection.sender.send(
            """{"id":0,"result":{"body":"Zm9v","base64Encoded":true},"sessionId":"56789"}""",
        )
        await wait_all_tasks_blocked()
        assert websocket_connection.sent == [
            """{"id":0,"method":"Fetch.getResponseBody","params":{"requestId":"request-1"},"sessionId":"56789"}""",
            (
                """{"id":1,"method":"Fetch.fulfillRequest","params":"""
                + """{"body":"Rk9P","requestId":"request-1","responseCode":401,"""
                + """"responseHeaders":[{"name":"a","value":"b"},{"name":"c","value":"e"}]},"sessionId":"56789"}"""
            ),
        ]

        await websocket_connection.sender.send("""{"id":1,"result":{},"sessionId":"56789"}""")
        await wait_all_tasks_blocked()
        assert "request-1" in cdp_client_session._requests_handled


class TestOnFetchRequestPaused:
    @pytest.mark.trio()
    async def test_unhandled_continue(
        self,
        monkeypatch: pytest.MonkeyPatch,
        cdp_client_session: CDPClientSession,
        websocket_connection: FakeWebsocketConnection,
        nursery: trio.Nursery,
    ):
        mock_fail_request = AsyncMock()
        mock_continue_request = AsyncMock()
        monkeypatch.setattr(cdp_client_session, "fail_request", mock_fail_request)
        monkeypatch.setattr(cdp_client_session, "continue_request", mock_continue_request)

        handler_foo = async_handler()
        handler_bar = async_handler()
        cdp_client_session.add_request_handler(handler_foo, url_pattern="http://foo/")
        cdp_client_session.add_request_handler(handler_bar, url_pattern="http://bar/")

        nursery.start_soon(cdp_client_session._on_fetch_request_paused)
        await wait_all_tasks_blocked()

        # language=json
        await websocket_connection.sender.send("""
            {
                "method": "Fetch.requestPaused",
                "params": {
                    "requestId": "request-1",
                    "frameId": "frame-1",
                    "request": {
                        "url": "http://bar/",
                        "method": "GET",
                        "headers": {},
                        "initialPriority": "VeryHigh",
                        "referrerPolicy": "strict-origin-when-cross-origin"
                    },
                    "resourceType": "Document",
                    "responseStatusCode": 200
                },
                "sessionId": "56789"
            }
        """)
        await wait_all_tasks_blocked()
        assert "request-1" not in cdp_client_session._requests_handled
        assert handler_foo.call_args_list == []
        assert handler_bar.call_args_list == [call(cdp_client_session, ANY)]
        assert isinstance(handler_bar.call_args_list[0][0][1], RequestPaused)
        assert mock_fail_request.call_args_list == []
        assert mock_continue_request.call_args_list == [call(ANY)]
        assert isinstance(mock_continue_request.call_args_list[0][0][0], RequestPaused)

    @pytest.mark.trio()
    async def test_unhandled_fail(
        self,
        monkeypatch: pytest.MonkeyPatch,
        cdp_client_session: CDPClientSession,
        websocket_connection: FakeWebsocketConnection,
        nursery: trio.Nursery,
    ):
        # make unhandled requests fail
        cdp_client_session._fail_unhandled = True

        mock_fail_request = AsyncMock()
        mock_continue_request = AsyncMock()
        monkeypatch.setattr(cdp_client_session, "fail_request", mock_fail_request)
        monkeypatch.setattr(cdp_client_session, "continue_request", mock_continue_request)

        handler_foo = async_handler()
        handler_bar = async_handler()
        cdp_client_session.add_request_handler(handler_foo, url_pattern="http://foo/")
        cdp_client_session.add_request_handler(handler_bar, url_pattern="http://bar/")

        nursery.start_soon(cdp_client_session._on_fetch_request_paused)
        await wait_all_tasks_blocked()

        # language=json
        await websocket_connection.sender.send("""
            {
                "method": "Fetch.requestPaused",
                "params": {
                    "requestId": "request-1",
                    "frameId": "frame-1",
                    "request": {
                        "url": "http://bar/",
                        "method": "GET",
                        "headers": {},
                        "initialPriority": "VeryHigh",
                        "referrerPolicy": "strict-origin-when-cross-origin"
                    },
                    "resourceType": "Document",
                    "responseStatusCode": 200
                },
                "sessionId": "56789"
            }
        """)
        await wait_all_tasks_blocked()
        assert "request-1" not in cdp_client_session._requests_handled
        assert handler_foo.call_args_list == []
        assert handler_bar.call_args_list == [call(cdp_client_session, ANY)]
        assert isinstance(handler_bar.call_args_list[0][0][1], RequestPaused)
        assert mock_fail_request.call_args_list == [call(ANY)]
        assert mock_continue_request.call_args_list == []
        assert isinstance(mock_fail_request.call_args_list[0][0][0], RequestPaused)

    @pytest.mark.trio()
    async def test_handled(
        self,
        monkeypatch: pytest.MonkeyPatch,
        cdp_client_session: CDPClientSession,
        websocket_connection: FakeWebsocketConnection,
        nursery: trio.Nursery,
    ):
        # make unhandled requests fail
        cdp_client_session._fail_unhandled = True

        mock_fail_request = AsyncMock()
        mock_continue_request = AsyncMock()
        monkeypatch.setattr(cdp_client_session, "fail_request", mock_fail_request)
        monkeypatch.setattr(cdp_client_session, "continue_request", mock_continue_request)

        def mock_handled(_cdp_client_session: CDPClientSession, request: RequestPaused):
            # pretend that we've called any of the request methods which register that the request was handled appropriately
            _cdp_client_session._requests_handled.add(request.request_id)

        handler_foo = async_handler()
        handler_bar = async_handler(side_effect=mock_handled)
        cdp_client_session.add_request_handler(handler_foo, url_pattern="http://foo/")
        cdp_client_session.add_request_handler(handler_bar, url_pattern="http://bar/")

        nursery.start_soon(cdp_client_session._on_fetch_request_paused)
        await wait_all_tasks_blocked()

        # language=json
        await websocket_connection.sender.send("""
            {
                "method": "Fetch.requestPaused",
                "params": {
                    "requestId": "request-1",
                    "frameId": "frame-1",
                    "request": {
                        "url": "http://bar/",
                        "method": "GET",
                        "headers": {},
                        "initialPriority": "VeryHigh",
                        "referrerPolicy": "strict-origin-when-cross-origin"
                    },
                    "resourceType": "Document",
                    "responseStatusCode": 200
                },
                "sessionId": "56789"
            }
        """)
        await wait_all_tasks_blocked()
        assert "request-1" in cdp_client_session._requests_handled
        assert handler_foo.call_args_list == []
        assert handler_bar.call_args_list == [call(cdp_client_session, ANY)]
        assert isinstance(handler_bar.call_args_list[0][0][1], RequestPaused)
        assert mock_fail_request.call_args_list == []
        assert mock_continue_request.call_args_list == []
