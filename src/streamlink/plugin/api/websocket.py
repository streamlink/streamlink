import json
import logging
from threading import Thread
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import unquote_plus, urlparse

from websocket import ABNF, STATUS_NORMAL, WebSocketApp, enableTrace

from streamlink.logger import TRACE, root as rootlogger
from streamlink.session import Streamlink


log = logging.getLogger(__name__)


class WebsocketClient(Thread):
    _id: int = 0

    def __init__(
        self,
        session: Streamlink,
        url: str,
        subprotocols: Optional[List[str]] = None,
        header: Optional[Union[List, Dict]] = None,
        cookie: Optional[str] = None,
        sockopt: Optional[Tuple] = None,
        sslopt: Optional[Dict] = None,
        host: Optional[str] = None,
        origin: Optional[str] = None,
        suppress_origin: bool = False,
        ping_interval: Union[int, float] = 0,
        ping_timeout: Optional[Union[int, float]] = None,
        ping_payload: str = ""
    ):
        if rootlogger.level <= TRACE:
            enableTrace(True, log)

        if not header:
            header = []
        if not any(True for h in header if h.startswith("User-Agent: ")):
            header.append(f"User-Agent: {session.http.headers['User-Agent']}")

        proxy_options = {}
        http_proxy: Optional[str] = session.get_option("http-proxy")
        if http_proxy:
            p = urlparse(http_proxy)
            proxy_options["proxy_type"] = p.scheme
            proxy_options["http_proxy_host"] = p.hostname
            if p.port:  # pragma: no branch
                proxy_options["http_proxy_port"] = p.port
            if p.username:  # pragma: no branch
                proxy_options["http_proxy_auth"] = unquote_plus(p.username), unquote_plus(p.password or "")

        self.session = session
        self.ws = WebSocketApp(
            url=url,
            subprotocols=subprotocols,
            header=header,
            cookie=cookie,
            on_open=self.on_open,
            on_error=self.on_error,
            on_close=self.on_close,
            on_ping=self.on_ping,
            on_pong=self.on_pong,
            on_message=self.on_message,
            on_cont_message=self.on_cont_message,
            on_data=self.on_data
        )
        self._data = dict(
            sockopt=sockopt,
            sslopt=sslopt,
            host=host,
            origin=origin,
            suppress_origin=suppress_origin,
            ping_interval=ping_interval,
            ping_timeout=ping_timeout,
            ping_payload=ping_payload,
            **proxy_options
        )

        self._id += 1
        super().__init__(
            name=f"Thread-{self.__class__.__name__}-{self._id}",
            daemon=True
        )

    def run(self) -> None:
        self.ws.run_forever(**self._data)

    # ----

    def close(self, status: int = STATUS_NORMAL, reason: Union[str, bytes] = "", timeout: int = 3) -> None:
        self.ws.close(status=status, reason=bytes(reason, encoding="utf-8"), timeout=timeout)
        if self.is_alive():  # pragma: no branch
            self.join()

    def send(self, data: Union[str, bytes], opcode: int = ABNF.OPCODE_TEXT) -> None:
        return self.ws.send(data, opcode)

    def send_json(self, data: Any) -> None:
        return self.send(json.dumps(data, indent=None, separators=(",", ":")))

    # ----

    # noinspection PyMethodMayBeStatic
    def on_open(self, wsapp: WebSocketApp) -> None:
        log.debug(f"Connected: {wsapp.url}")  # pragma: no cover

    # noinspection PyMethodMayBeStatic
    # noinspection PyUnusedLocal
    def on_error(self, wsapp: WebSocketApp, error: Exception) -> None:
        log.error(error)  # pragma: no cover

    # noinspection PyMethodMayBeStatic
    # noinspection PyUnusedLocal
    def on_close(self, wsapp: WebSocketApp, status: int, message: str) -> None:
        log.debug(f"Closed: {wsapp.url}")  # pragma: no cover

    def on_ping(self, wsapp: WebSocketApp, data: str) -> None:
        pass  # pragma: no cover

    def on_pong(self, wsapp: WebSocketApp, data: str) -> None:
        pass  # pragma: no cover

    def on_message(self, wsapp: WebSocketApp, data: str) -> None:
        pass  # pragma: no cover

    def on_cont_message(self, wsapp: WebSocketApp, data: str, cont: Any) -> None:
        pass  # pragma: no cover

    def on_data(self, wsapp: WebSocketApp, data: str, data_type: int, cont: Any) -> None:
        pass  # pragma: no cover
