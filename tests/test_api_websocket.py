import unittest
from threading import Event
from unittest.mock import Mock, call, patch

from websocket import ABNF, STATUS_NORMAL

from streamlink.logger import DEBUG, TRACE
from streamlink.plugin.api.websocket import WebsocketClient
from streamlink.session import Streamlink


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
                sslopt={"ssloptkey": "ssloptval"},
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
        self.assertFalse(client.is_alive())
        self.assertTrue(client.status)
        self.assertEqual(mock_ws_close.call_args_list, [
            call(
                status=STATUS_NORMAL,
                reason=b"foo",
                timeout=3
            )
        ])
