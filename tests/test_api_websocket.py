from unittest.mock import ANY, Mock, call, patch

import pytest
from websocket import ABNF, STATUS_NORMAL  # type: ignore[import]

from streamlink.logger import DEBUG, TRACE
from streamlink.plugin.api.useragents import FIREFOX
from streamlink.plugin.api.websocket import WebsocketClient
from streamlink.session import Streamlink
from tests.testutils.handshake import Handshake


@pytest.mark.parametrize(("name", "value"), [
    ("OPCODE_CONT", ABNF.OPCODE_CONT),
    ("OPCODE_TEXT", ABNF.OPCODE_TEXT),
    ("OPCODE_BINARY", ABNF.OPCODE_BINARY),
    ("OPCODE_CLOSE", ABNF.OPCODE_CLOSE),
    ("OPCODE_PING", ABNF.OPCODE_PING),
    ("OPCODE_PONG", ABNF.OPCODE_PONG),
])
def test_opcode_export(name, value):
    assert getattr(WebsocketClient, name) == value


class TestWebsocketClient:
    @pytest.fixture()
    def session(self, request: pytest.FixtureRequest):
        with patch("streamlink.session.Streamlink.load_builtin_plugins"):
            session = Streamlink()
            for key, value in getattr(request, "param", {}).items():
                session.set_option(key, value)
            yield session

    @pytest.fixture()
    def websocketapp(self):
        with patch("streamlink.plugin.api.websocket.WebSocketApp") as mock_websocketapp:
            yield mock_websocketapp

    @pytest.fixture()
    def client(self, request: pytest.FixtureRequest, session: Streamlink, websocketapp: Mock):
        with patch("streamlink.plugin.api.websocket.certify_where", side_effect=Mock(return_value="/path/to/cacert.pem")):
            yield WebsocketClient(session, "wss://localhost:0", **getattr(request, "param", {}))

    @pytest.mark.parametrize(("level", "expected"), [
        pytest.param(DEBUG, False, id="debug"),
        pytest.param(TRACE, True, id="trace"),
    ])
    def test_log(self, session: Streamlink, level: int, expected: bool):
        with patch("streamlink.plugin.api.websocket.enableTrace") as mock_enable_trace, \
             patch("streamlink.plugin.api.websocket.rootlogger", Mock(level=level)):
            WebsocketClient(session, "wss://localhost:0")
        assert mock_enable_trace.called is expected

    @pytest.mark.parametrize(("client", "expected"), [
        pytest.param({}, FIREFOX, id="default"),
        pytest.param({"header": ["User-Agent: foo"]}, "foo", id="header list"),
        pytest.param({"header": {"User-Agent": "bar"}}, "bar", id="header dict"),
    ], indirect=["client"])
    def test_user_agent(self, client: WebsocketClient, websocketapp: Mock, expected: str):
        assert [arg[1].get("header", []) for arg in websocketapp.call_args_list] == [[f"User-Agent: {expected}"]]

    @pytest.mark.parametrize(("session", "client"), [
        (
            {
                "http-proxy": "https://username:password@hostname:1234",
            },
            {
                "subprotocols": ["sub1", "sub2"],
                "cookie": "cookie",
                "sockopt": ("sockopt1", "sockopt2"),
                "sslopt": {"ssloptkey": "ssloptval"},
                "host": "customhost",
                "origin": "customorigin",
                "suppress_origin": True,
                "ping_interval": 30,
                "ping_timeout": 4,
                "ping_payload": "ping",
            },
        ),
    ], indirect=["session", "client"])
    def test_args_and_proxy(self, session: Streamlink, client: WebsocketClient, websocketapp: Mock):
        assert websocketapp.call_args_list == [
            call(
                url="wss://localhost:0",
                subprotocols=["sub1", "sub2"],
                cookie="cookie",
                header=ANY,
                on_open=ANY,
                on_error=ANY,
                on_close=ANY,
                on_ping=ANY,
                on_pong=ANY,
                on_message=ANY,
                on_cont_message=ANY,
                on_data=ANY,
            ),
        ]
        with patch.object(client.ws, "run_forever") as mock_ws_run_forever:
            client.start()
            client.join(1)
        assert not client.is_alive()
        assert mock_ws_run_forever.call_args_list == [
            call(
                sockopt=("sockopt1", "sockopt2"),
                sslopt={
                    "ssloptkey": "ssloptval",
                    "ca_certs": "/path/to/cacert.pem",
                },
                host="customhost",
                origin="customorigin",
                suppress_origin=True,
                ping_interval=30,
                ping_timeout=4,
                ping_payload="ping",
                proxy_type="https",
                http_proxy_host="hostname",
                http_proxy_port=1234,
                http_proxy_auth=("username", "password"),
            ),
        ]

    def test_handlers(self, session: Streamlink):
        client = WebsocketClient(session, "wss://localhost:0")
        assert client.ws.on_open == client.on_open
        assert client.ws.on_error == client.on_error
        assert client.ws.on_close == client.on_close
        assert client.ws.on_ping == client.on_ping
        assert client.ws.on_pong == client.on_pong
        assert client.ws.on_message == client.on_message
        assert client.ws.on_cont_message == client.on_cont_message
        assert client.ws.on_data == client.on_data

    def test_send(self, client: WebsocketClient):
        with patch.object(client, "ws") as mock_ws:
            client.send("foo")
            client.send(b"foo", ABNF.OPCODE_BINARY)
            client.send_json({"foo": "bar", "baz": "qux"})
        assert mock_ws.send.call_args_list == [
            call("foo", ABNF.OPCODE_TEXT),
            call(b"foo", ABNF.OPCODE_BINARY),
            call("{\"foo\":\"bar\",\"baz\":\"qux\"}", ABNF.OPCODE_TEXT),
        ]

    def test_close(self, session: Streamlink):
        handshake = Handshake()

        class WebsocketClientSubclass(WebsocketClient):
            def run(self):
                with handshake():
                    pass

        client = WebsocketClientSubclass(session, "wss://localhost:0")
        with patch.object(client.ws, "close") as mock_ws_close:
            mock_ws_close.side_effect = lambda *_, **__: handshake.go()
            client.start()
            client.close(reason="foo")
        assert handshake.wait_done(1)
        assert not client.is_alive()
        assert mock_ws_close.call_args_list == [call(status=STATUS_NORMAL, reason=b"foo", timeout=3)]

    def test_close_self(self, session: Streamlink):
        handshake = Handshake()

        class WebsocketClientSubclass(WebsocketClient):
            def run(self):
                with handshake(Exception):
                    self.close(reason=b"bar")

        client = WebsocketClientSubclass(session, "wss://localhost:0")
        client.start()
        assert handshake.step(1)
        client.join(timeout=4)
        assert not client.is_alive()
        assert handshake._context.error is None, "Doesn't join current thread"

    def test_reconnect_disconnected(self, client: WebsocketClient, websocketapp: Mock):
        handshake = Handshake()

        # noinspection PyUnusedLocal
        def mock_run_forever(**data):
            client.ws.keep_running = False
            with handshake():
                pass

        client.ws.keep_running = True
        client.ws.run_forever.side_effect = mock_run_forever

        client.start()
        assert handshake.step(1), "Enters run_forever loop on ws client thread"
        assert websocketapp.call_count == 1
        client.reconnect()
        assert websocketapp.call_count == 1, "Doesn't reconnect if disconnected"
        client.join(timeout=4)
        assert not client.is_alive()

    def test_reconnect_once(self, client: WebsocketClient, websocketapp: Mock):
        handshake = Handshake()

        # noinspection PyUnusedLocal
        def mock_run_forever(**data):
            with handshake():
                pass

        client.ws.keep_running = True
        client.ws.run_forever.side_effect = mock_run_forever

        client.start()
        assert client.ws.close.call_count == 0
        assert websocketapp.call_count == 1, "Creates initial connection"
        assert not client._reconnect, "Has not set the _reconnect state"
        assert handshake.wait_ready(1), "Enters run_forever loop on client thread"

        client.reconnect()
        assert client.ws.close.call_count == 1
        assert websocketapp.call_count == 2, "Creates new connection"
        assert client._reconnect, "Has set the _reconnect state"

        assert handshake.step(1)
        assert handshake.wait_ready(1), "Enters run_forever loop on client thread again"
        assert not client._reconnect, "Has reset the _reconnect state"

        assert handshake.step(1)
        assert not handshake.wait_ready(0), "Doesn't enter run_forever loop on client thread again"
        client.join(1)
        assert not client.is_alive()
        assert websocketapp.call_count == 2, "Connection has ended regularly"
