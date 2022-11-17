import unittest
from threading import Event
from unittest.mock import Mock, call, patch

import pytest
from websocket import ABNF, STATUS_NORMAL  # type: ignore[import]

from streamlink.logger import DEBUG, TRACE
from streamlink.plugin.api.websocket import WebsocketClient
from streamlink.session import Streamlink


@pytest.mark.parametrize("name,value", [
    ("OPCODE_CONT", ABNF.OPCODE_CONT),
    ("OPCODE_TEXT", ABNF.OPCODE_TEXT),
    ("OPCODE_BINARY", ABNF.OPCODE_BINARY),
    ("OPCODE_CLOSE", ABNF.OPCODE_CLOSE),
    ("OPCODE_PING", ABNF.OPCODE_PING),
    ("OPCODE_PONG", ABNF.OPCODE_PONG),
])
def test_opcode_export(name, value):
    assert getattr(WebsocketClient, name) == value


class TestWebsocketClient(unittest.TestCase):
    def setUp(self):
        self.session = Streamlink()

    def tearDown(self):
        self.session = None

    @patch("streamlink.plugin.api.websocket.enableTrace")
    def test_log(self, mock_enable_trace: Mock):
        with patch("streamlink.plugin.api.websocket.rootlogger", Mock(level=DEBUG)):
            WebsocketClient(self.session, "wss://localhost:0")
        self.assertFalse(mock_enable_trace.called)

        with patch("streamlink.plugin.api.websocket.rootlogger", Mock(level=TRACE)):
            WebsocketClient(self.session, "wss://localhost:0")
        self.assertTrue(mock_enable_trace.called)

    def test_user_agent(self):
        client = WebsocketClient(self.session, "wss://localhost:0")
        self.assertEqual(client.ws.header, [
            f"User-Agent: {self.session.http.headers['User-Agent']}"
        ])

        client = WebsocketClient(self.session, "wss://localhost:0", header=["User-Agent: foo"])
        self.assertEqual(client.ws.header, [
            "User-Agent: foo"
        ])

        client = WebsocketClient(self.session, "wss://localhost:0", header={"User-Agent": "bar"})
        self.assertEqual(client.ws.header, [
            "User-Agent: bar"
        ])

    @patch("streamlink.plugin.api.websocket.certify_where", Mock(side_effect=lambda: "/path/to/cacert.pem"))
    def test_args_and_proxy(self):
        self.session.set_option("http-proxy", "https://username:password@hostname:1234")
        client = WebsocketClient(
            self.session,
            "wss://localhost:0",
            subprotocols=["sub1", "sub2"],
            cookie="cookie",
            sockopt=("sockopt1", "sockopt2"),
            sslopt={"ssloptkey": "ssloptval"},
            host="customhost",
            origin="customorigin",
            suppress_origin=True,
            ping_interval=30,
            ping_timeout=4,
            ping_payload="ping"
        )
        self.assertEqual(client.ws.url, "wss://localhost:0")
        self.assertEqual(client.ws.subprotocols, ["sub1", "sub2"])
        self.assertEqual(client.ws.cookie, "cookie")
        with patch.object(client.ws, "run_forever") as mock_ws_run_forever:
            client.start()
            client.join(1)
        self.assertFalse(client.is_alive())
        self.assertEqual(mock_ws_run_forever.call_args_list, [
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
                http_proxy_auth=("username", "password")
            )
        ])

    def test_handlers(self):
        client = WebsocketClient(self.session, "wss://localhost:0")
        self.assertEqual(client.ws.on_open, client.on_open)
        self.assertEqual(client.ws.on_error, client.on_error)
        self.assertEqual(client.ws.on_close, client.on_close)
        self.assertEqual(client.ws.on_ping, client.on_ping)
        self.assertEqual(client.ws.on_pong, client.on_pong)
        self.assertEqual(client.ws.on_message, client.on_message)
        self.assertEqual(client.ws.on_cont_message, client.on_cont_message)
        self.assertEqual(client.ws.on_data, client.on_data)

    def test_send(self):
        client = WebsocketClient(self.session, "wss://localhost:0")
        with patch.object(client, "ws") as mock_ws:
            client.send("foo")
            client.send(b"foo", ABNF.OPCODE_BINARY)
            client.send_json({"foo": "bar", "baz": "qux"})
        self.assertEqual(mock_ws.send.call_args_list, [
            call("foo", ABNF.OPCODE_TEXT),
            call(b"foo", ABNF.OPCODE_BINARY),
            call("{\"foo\":\"bar\",\"baz\":\"qux\"}", ABNF.OPCODE_TEXT),
        ])

    def test_close(self):
        class WebsocketClientSubclass(WebsocketClient):
            running = Event()
            status = False

            def run(self):
                self.status = self.running.wait(4)

        client = WebsocketClientSubclass(self.session, "wss://localhost:0")
        with patch.object(client.ws, "close") as mock_ws_close:
            mock_ws_close.side_effect = lambda *_, **__: client.running.set()
            client.start()
            client.close(reason="foo")
        assert not client.is_alive()
        assert client.status
        assert mock_ws_close.call_args_list == [call(status=STATUS_NORMAL, reason=b"foo", timeout=3)]

    def test_close_self(self):
        class WebsocketClientSubclass(WebsocketClient):
            status = None

            def run(self):
                try:
                    self.close(reason=b"bar")
                except RuntimeError as err:  # pragma: no cover
                    self.status = err

        client = WebsocketClientSubclass(self.session, "wss://localhost:0")
        client.start()
        client.join(timeout=4)
        assert not client.is_alive()
        assert client.status is None, "Doesn't join current thread"

    @patch("streamlink.plugin.api.websocket.WebSocketApp")
    def test_reconnect_disconnected(self, mock_wsapp: Mock):
        client = WebsocketClient(self.session, "wss://localhost:0")
        event_run_forever_entered = Event()

        # noinspection PyUnusedLocal
        def mock_run_forever(**data):
            client.ws.keep_running = False
            event_run_forever_entered.set()

        client.ws.keep_running = True
        client.ws.run_forever.side_effect = mock_run_forever

        client.start()
        self.assertTrue(event_run_forever_entered.wait(1), "Enters run_forever loop on ws client thread")
        self.assertEqual(mock_wsapp.call_count, 1)
        client.reconnect()
        self.assertEqual(mock_wsapp.call_count, 1, "Doesn't reconnect if disconnected")
        client.join()

    @patch("streamlink.plugin.api.websocket.WebSocketApp")
    def test_reconnect_once(self, mock_wsapp: Mock):
        client = WebsocketClient(self.session, "wss://localhost:0")
        run_forever_entered = Event()
        run_forever_ended = Event()

        # noinspection PyUnusedLocal
        def mock_run_forever(**data):
            run_forever_entered.set()
            run_forever_ended.wait(1)
            run_forever_ended.clear()

        client.ws.keep_running = True
        client.ws.run_forever.side_effect = mock_run_forever

        client.start()
        self.assertEqual(client.ws.close.call_count, 0)
        self.assertEqual(mock_wsapp.call_count, 1, "Creates initial connection")
        self.assertFalse(client._reconnect, "Has not set the _reconnect state")
        self.assertTrue(run_forever_entered.wait(1), "Enters run_forever loop on client thread")
        run_forever_entered.clear()

        client.reconnect()
        self.assertEqual(client.ws.close.call_count, 1)
        self.assertEqual(mock_wsapp.call_count, 2, "Creates new connection")
        self.assertTrue(client._reconnect, "Has set the _reconnect state")

        run_forever_ended.set()
        self.assertTrue(run_forever_entered.wait(1), "Enters run_forever loop on client thread again")
        self.assertFalse(client._reconnect, "Has reset the _reconnect state")

        run_forever_ended.set()
        client.join(1)
        self.assertFalse(client.is_alive())
        self.assertEqual(mock_wsapp.call_count, 2, "Connection has ended regularly")
