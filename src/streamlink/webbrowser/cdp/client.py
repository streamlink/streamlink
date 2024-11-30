from __future__ import annotations

import base64
import re
from collections.abc import AsyncGenerator, Awaitable, Callable, Coroutine, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import trio

from streamlink.session import Streamlink
from streamlink.webbrowser.cdp.connection import CDPConnection, CDPSession
from streamlink.webbrowser.cdp.devtools import fetch, network, page, runtime, target
from streamlink.webbrowser.cdp.exceptions import CDPError
from streamlink.webbrowser.chromium import ChromiumWebbrowser


if TYPE_CHECKING:
    try:
        from typing import Self, TypeAlias  # type: ignore[attr-defined]
    except ImportError:
        from typing_extensions import Self, TypeAlias


TRequestHandlerCallable: TypeAlias = "Callable[[CDPClientSession, fetch.RequestPaused], Awaitable]"


_re_url_pattern_wildcard = re.compile(r"(.+?)?(\\+)?([*?])")


@dataclass
class RequestPausedHandler:
    async_handler: TRequestHandlerCallable
    url_pattern: str = "*"
    on_request: bool = False

    def __post_init__(self) -> None:
        self._re_url: re.Pattern = self._url_pattern_to_regex_pattern(self.url_pattern)

    def matches(self, request: fetch.RequestPaused) -> bool:
        on_request: bool = request.response_status_code is None and request.response_error_reason is None
        return on_request is self.on_request and self._re_url.match(request.request.url) is not None

    @staticmethod
    def _url_pattern_to_regex_pattern(url_pattern: str) -> re.Pattern:
        pos = 0
        regex = ""

        for match in _re_url_pattern_wildcard.finditer(url_pattern):
            regex += re.escape(match[1]) if match[1] else ""
            if match[2]:
                if len(match[2]) % 2:
                    regex += f"{re.escape(match[2][:-1])}\\{match[3]}"
                else:
                    regex += re.escape(match[2])
                    regex += ".+" if match[3] == "*" else "."
            else:
                regex += ".+" if match[3] == "*" else "."

            pos = match.end()

        regex += re.escape(url_pattern[pos:])

        return re.compile(f"^{regex}$")


@dataclass
class CMRequestProxy:
    body: str
    response_code: int
    response_headers: Mapping[str, str] | None


class CDPClient:
    """
    The public interface around :class:`ChromiumWebbrowser <streamlink.webbrowser.chromium.ChromiumWebbrowser>`
    and :class:`CDPConnection <streamlink.webbrowser.cdp.connection.CDPConnection>`.

    It launches the Chromium-based web browser, establishes the remote debugging WebSocket connection using
    the `Chrome Devtools Protocol <https://chromedevtools.github.io/devtools-protocol/>`_,  and provides
    the :meth:`session()` method for creating a new :class:`CDPClientSession` that is tied to an empty new browser tab.

    :class:`CDPClientSession` provides a high-level API for navigating websites, intercepting network requests and responses,
    as well as evaluating JavaScript expressions and retrieving async results.

    Don't instantiate this class yourself, use the :meth:`CDPClient.launch()` async context manager classmethod.

    For low-level Chrome Devtools Protocol interfaces, please see Streamlink's automatically generated
    ``streamlink.webbrowser.cdp.devtools`` package, but be aware that only a subset of the available domains is supported.
    """

    def __init__(self, cdp_connection: CDPConnection, nursery: trio.Nursery, headless: bool):
        self.cdp_connection = cdp_connection
        self.nursery = nursery
        self.headless = headless

    @classmethod
    def launch(
        cls,
        session: Streamlink,
        runner: Callable[[Self], Coroutine],
        executable: str | None = None,
        timeout: float | None = None,
        cdp_host: str | None = None,
        cdp_port: int | None = None,
        cdp_timeout: float | None = None,
        headless: bool | None = None,
    ) -> Any:
        """
        Start a new :mod:`trio` runloop and do the following things:

        1. Launch the Chromium-based web browser using the provided parameters or respective session options
        2. Initialize a new :class:`CDPConnection <streamlink.webbrowser.cdp.connection.CDPConnection>`
           and connect to the browser's remote debugging interface
        3. Create a new :class:`CDPClient` instance
        4. Execute the async runner callback with the :class:`CDPClient` instance as only argument

        If the ``webbrowser`` session option is set to ``False``, then a :exc:`CDPError` will be raised.

        Example:

        .. code-block:: python

            async def fake_response(client_session: CDPClientSession, request: devtools.fetch.RequestPaused):
                if request.response_status_code is not None and 300 <= request.response_status_code < 400:
                    await client_session.continue_request(request)
                else:
                    async with client_session.alter_request(request) as cmproxy:
                        cmproxy.body = "<!doctype html><html><body>foo</body></html>"

            async def my_app_logic(client: CDPClient):
                async with client.session() as client_session:
                    client_session.add_request_handler(fake_response, "*")
                    async with client_session.navigate("https://google.com") as frame_id:
                        await client_session.loaded(frame_id)
                        return await client_session.evaluate("document.body.innerText")

            assert CDPClient.launch(session, my_app_logic) == "foo"

        :param session:     The Streamlink session object
        :param runner:      An async client callback function which receives the :class:`CDPClient` instance as only parameter.
        :param executable:  Optional path to the Chromium-based web browser executable.
                            If unset, falls back to the ``webbrowser-executable`` session option.
                            Otherwise, it'll be looked up according to the rules of the :class:`ChromiumBrowser` implementation.
        :param timeout:     Optional global timeout value, including web browser launch time.
                            If unset, falls back to the ``webbrowser-timeout`` session option.
        :param cdp_host:    Optional remote debugging host.
                            If unset, falls back to the ``webbrowser-cdp-host`` session option.
                            Otherwise, ``127.0.0.1`` will be used.
        :param cdp_port:    Optional remote debugging port.
                            If unset, falls back to the ``webbrowser-cdp-port`` session option.
                            Otherwise, a random free port will be chosen.
        :param cdp_timeout: Optional CDP command timeout value.
                            If unset, falls back to the ``webbrowser-cdp-timeout`` session option.
        :param headless:    Optional boolean flag whether to launch the web browser in headless mode or not.
                            If unset, falls back to the ``webbrowser-headless`` session option.
        """
        if not session.get_option("webbrowser"):
            raise CDPError("The webbrowser API has been disabled by the user")

        async def run_wrapper() -> Any:
            async with cls.run(
                session=session,
                executable=session.get_option("webbrowser-executable") if executable is None else executable,
                timeout=session.get_option("webbrowser-timeout") if timeout is None else timeout,
                cdp_host=session.get_option("webbrowser-cdp-host") if cdp_host is None else cdp_host,
                cdp_port=session.get_option("webbrowser-cdp-port") if cdp_port is None else cdp_port,
                cdp_timeout=session.get_option("webbrowser-cdp-timeout") if cdp_timeout is None else cdp_timeout,
                headless=session.get_option("webbrowser-headless") if headless is None else headless,
            ) as cdp_client:
                return await runner(cdp_client)

        return trio.run(run_wrapper, strict_exception_groups=True)

    @classmethod
    @asynccontextmanager
    async def run(
        cls,
        session: Streamlink,
        executable: str | None = None,
        timeout: float | None = None,
        cdp_host: str | None = None,
        cdp_port: int | None = None,
        cdp_timeout: float | None = None,
        headless: bool = False,
    ) -> AsyncGenerator[Self, None]:
        webbrowser = ChromiumWebbrowser(executable=executable, host=cdp_host, port=cdp_port)
        nursery: trio.Nursery
        async with webbrowser.launch(headless=headless, timeout=timeout) as nursery:
            websocket_url = webbrowser.get_websocket_url(session)
            cdp_connection: CDPConnection
            async with CDPConnection.create(websocket_url, timeout=cdp_timeout) as cdp_connection:
                yield cls(cdp_connection, nursery, headless)

    @asynccontextmanager
    async def session(
        self,
        fail_unhandled_requests: bool = False,
        max_buffer_size: int | None = None,
    ) -> AsyncGenerator[CDPClientSession, None]:
        """
        Create a new CDP session on an empty target (browser tab).

        :param fail_unhandled_requests: Whether network requests which are not matched by any request handlers should fail.
        :param max_buffer_size: Optional size of the send/receive memory channel for paused HTTP requests/responses.
        """
        cdp_session = await self.cdp_connection.new_target()
        yield CDPClientSession(self, cdp_session, fail_unhandled_requests, max_buffer_size)


class CDPClientSession:
    """
    High-level API for navigating websites, intercepting network requests/responses,
    and for evaluating async JavaScript expressions.

    Don't instantiate this class yourself, use the :meth:`CDPClient.session()` async contextmanager.
    """

    def __init__(
        self,
        cdp_client: CDPClient,
        cdp_session: CDPSession,
        fail_unhandled_requests: bool = False,
        max_buffer_size: int | None = None,
    ):
        self.cdp_client = cdp_client
        self.cdp_session = cdp_session
        self._fail_unhandled = fail_unhandled_requests
        self._request_handlers: list[RequestPausedHandler] = []
        self._requests_handled: set[str] = set()
        self._max_buffer_size = max_buffer_size

    def add_request_handler(
        self,
        async_handler: TRequestHandlerCallable,
        url_pattern: str = "*",
        on_request: bool = False,
    ):
        """
        :param async_handler: An async request handler which must call :meth:`continue_request()`, :meth:`fail_request()`,
                              :meth:`fulfill_request()` or :meth:`alter_request()`, or the next matching request handler
                              will be run. If no matching request handler was found or if no matching one called one of
                              the just mentioned methods, then the request will be continued if the session was initialized
                              with ``fail_unhandled_requests=False``, otherwise it will be blocked.
        :param url_pattern:   An optional URL wildcard string which defaults to ``"*"``. Only matching URLs will cause
                              ``Fetch.requestPraused`` events to be emitted over the CDP connection.
                              The async request handler will be called on each matching URL unless another request handler
                              has already handled the request (see description above).
        :param on_request:    Whether to intercept the network request or the network response.
        """
        self._request_handlers.append(
            RequestPausedHandler(async_handler=async_handler, url_pattern=url_pattern, on_request=on_request),
        )

    @asynccontextmanager
    async def navigate(self, url: str, referrer: str | None = None) -> AsyncGenerator[page.FrameId, None]:
        """
        Async context manager for opening the URL with an optional referrer and starting the optional interception
        of network requests and responses.
        If the target gets detached from the session, e.g. by closing the tab, then the whole CDP connection gets terminated,
        including all other concurrent sessions.
        Doesn't wait for the request to finish loading. See :meth:`loaded()`.

        :param url: The URL.
        :param referrer: An optional referrer.
        :return: Yields the ``FrameID`` that can be passed to the :meth:`loaded()` call.
        """

        request_patterns = [
            fetch.RequestPattern(
                url_pattern=url_pattern,
                request_stage=fetch.RequestStage.REQUEST if on_request else fetch.RequestStage.RESPONSE,
            )
            for url_pattern, on_request in sorted(
                {(request_handler.url_pattern, request_handler.on_request) for request_handler in self._request_handlers},
            )
        ]

        async with trio.open_nursery() as nursery:
            nursery.start_soon(self._on_target_detached_from_target)

            if self.cdp_client.headless:
                await self._update_user_agent()

            if request_patterns:
                nursery.start_soon(self._on_fetch_request_paused)
                await self.cdp_session.send(fetch.enable(request_patterns, True))

            await self.cdp_session.send(page.enable())

            try:
                frame_id, _loader_id, error = await self.cdp_session.send(page.navigate(url=url, referrer=referrer))
                if error:
                    raise CDPError(f"Navigation error: {error}")

                yield frame_id

            finally:
                await self.cdp_session.send(page.disable())
                if request_patterns:
                    await self.cdp_session.send(fetch.disable())
                nursery.cancel_scope.cancel()

    async def loaded(self, frame_id: page.FrameId):
        """
        Wait for the navigated page to finish loading.
        """
        async for frame_stopped_loading in self.cdp_session.listen(page.FrameStoppedLoading):  # pragma: no branch
            if frame_stopped_loading.frame_id == frame_id:
                return

    async def evaluate(self, expression: str, await_promise: bool = True, timeout: float | None = None) -> Any:
        """
        Evaluate an optionally async JavaScript expression and return its result.

        :param expression: The JavaScript expression.
        :param await_promise: Whether to await a returned :js:class:`Promise` object.
        :param timeout: Optional timeout override value. Uses the session's single CDP command timeout value by default,
                        which may be too short depending on the script execution time.
        :raise CDPError: On evaluation error or if the result is a subtype of :js:class:`window.Error`.
        :return: Only JS-primitive result values are supported, e.g. strings or numbers.
                 Other kinds of return values must be serialized, e.g. via :js:meth:`JSON.stringify()`.
        """
        evaluate = runtime.evaluate(
            expression=expression,
            await_promise=await_promise,
        )
        remote_obj, error = await self.cdp_session.send(evaluate, timeout=timeout)
        if error:
            raise CDPError(error.exception and error.exception.description or error.text)
        if remote_obj.type_ == "object" and remote_obj.subtype == "error":
            raise CDPError(remote_obj.description)
        return remote_obj.value

    async def continue_request(
        self,
        request: fetch.RequestPaused,
        url: str | None = None,
        method: str | None = None,
        post_data: str | None = None,
        headers: Mapping[str, str] | None = None,
    ):
        """
        Continue a request and optionally override the request method, URL, POST data or request headers.
        """
        await self.cdp_session.send(
            fetch.continue_request(
                request_id=request.request_id,
                url=url,
                method=method,
                post_data=base64.b64encode(post_data.encode()).decode() if post_data is not None else None,
                headers=self._headers_entries_from_mapping(headers),
            ),
        )
        self._requests_handled.add(request.request_id)

    async def fail_request(
        self,
        request: fetch.RequestPaused,
        error_reason: str | None = None,
    ):
        """
        Let a request fail, with an optional error reason which defaults to ``BlockedByClient``.
        """
        await self.cdp_session.send(
            fetch.fail_request(
                request_id=request.request_id,
                error_reason=network.ErrorReason(error_reason or network.ErrorReason.BLOCKED_BY_CLIENT),
            ),
        )
        self._requests_handled.add(request.request_id)

    async def fulfill_request(
        self,
        request: fetch.RequestPaused,
        response_code: int = 200,
        response_headers: Mapping[str, str] | None = None,
        body: str | None = None,
    ) -> None:
        """
        Fulfill a response and override its status code, headers and body.
        """
        await self.cdp_session.send(
            fetch.fulfill_request(
                request_id=request.request_id,
                response_code=response_code,
                response_headers=self._headers_entries_from_mapping(response_headers),
                body=base64.b64encode(body.encode()).decode() if body is not None else None,
            ),
        )
        self._requests_handled.add(request.request_id)

    @asynccontextmanager
    async def alter_request(
        self,
        request: fetch.RequestPaused,
        response_code: int = 200,
        response_headers: Mapping[str, str] | None = None,
    ) -> AsyncGenerator[CMRequestProxy, None]:
        """
        Async context manager wrapper around :meth:`fulfill_request()` which retrieves the response body,
        so it can be altered. The status code and headers can be altered in the method call directly,
        or by setting the respective parameters on the context manager's proxy object.
        """
        if request.response_status_code is None:
            body = ""
        else:
            body, b64encoded = await self.cdp_session.send(fetch.get_response_body(request.request_id))
            if b64encoded:  # pragma: no branch
                body = base64.b64decode(body).decode()
        proxy = CMRequestProxy(body=body, response_code=response_code, response_headers=response_headers)
        yield proxy
        await self.fulfill_request(
            request=request,
            response_code=proxy.response_code,
            response_headers=proxy.response_headers,
            body=proxy.body,
        )

    @staticmethod
    def _headers_entries_from_mapping(headers: Mapping[str, str] | None):
        return None if headers is None else [fetch.HeaderEntry(name=name, value=value) for name, value in headers.items()]

    async def _on_target_detached_from_target(self) -> None:
        detached_from_target: target.DetachedFromTarget
        async for detached_from_target in self.cdp_client.cdp_connection.listen(target.DetachedFromTarget):
            if detached_from_target.session_id == self.cdp_session.session_id:
                raise CDPError("Target has been detached")

    async def _on_fetch_request_paused(self) -> None:
        request: fetch.RequestPaused
        async for request in self.cdp_session.listen(fetch.RequestPaused, max_buffer_size=self._max_buffer_size):
            for handler in self._request_handlers:
                if not handler.matches(request):
                    continue
                await handler.async_handler(self, request)
                if request.request_id in self._requests_handled:
                    break
            else:
                if self._fail_unhandled:
                    await self.fail_request(request)
                else:
                    await self.continue_request(request)

    async def _update_user_agent(self) -> None:
        user_agent: str = await self.evaluate("navigator.userAgent", await_promise=False)
        if not user_agent:  # pragma: no cover
            raise CDPError("Could not read navigator.userAgent value")
        user_agent = re.sub(r"Headless", "", user_agent, flags=re.IGNORECASE)
        await self.cdp_session.send(network.set_user_agent_override(user_agent=user_agent))
