import socket
from contextlib import suppress
from http.server import BaseHTTPRequestHandler
from io import BytesIO
from typing import Optional

from streamlink_cli.output.abc import Output


class HTTPRequest(BaseHTTPRequestHandler):
    # noinspection PyMissingConstructor
    def __init__(self, request_text):
        self.rfile = BytesIO(request_text)
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()

    def send_error(self, code, message=None, explain=None):
        self.error_code = code
        self.error_message = message


class HTTPOutput(Output):
    socket: socket.socket

    def __init__(self, host: Optional[str] = "127.0.0.1", port: int = 0) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self.conn: Optional[socket.socket] = None

    @property
    def addresses(self):
        if self.host:
            return [self.host]

        addrs = {"127.0.0.1"}
        with suppress(socket.gaierror):
            for info in socket.getaddrinfo(socket.gethostname(), self.port, socket.AF_INET):
                addrs.add(info[4][0])

        return sorted(addrs)

    @property
    def urls(self):
        for addr in self.addresses:
            yield f"http://{addr}:{self.port}/"

    @property
    def url(self):
        return next(self.urls, None)

    def start_server(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host or "", self.port))
        self.socket.listen(1)
        self.host, self.port = self.socket.getsockname()
        if self.host == "0.0.0.0":
            self.host = None

    def accept_connection(self, timeout=30) -> None:
        self.socket.settimeout(timeout)

        try:
            conn, addr = self.socket.accept()
            conn.settimeout(None)
            self.conn = conn
        except socket.timeout as err:
            self.conn = None
            raise OSError("Socket accept timed out") from err

    def _open(self):
        conn = self.conn
        if not conn:
            raise OSError("No client connection")

        try:
            req_data = conn.recv(1024)
        except OSError as err:
            raise OSError("Failed to read data from socket") from err

        req = HTTPRequest(req_data)
        if req.command not in ("GET", "HEAD"):
            conn.send(b"HTTP/1.1 501 Not Implemented\r\n")
            conn.close()
            raise OSError(f"Invalid request method: {req.command}")

        try:
            conn.send(b"HTTP/1.1 200 OK\r\n")
            conn.send(b"Server: Streamlink\r\n")
            conn.send(b"Content-Type: video/unknown\r\n")
            conn.send(b"\r\n")
        except OSError as err:
            raise OSError("Failed to write data to socket") from err

        # We don't want to send any data on HEAD requests.
        if req.command == "HEAD":
            conn.close()
            raise OSError

        self.request = req

    def _write(self, data):
        self.conn.sendall(data)

    def _close(self):
        if self.conn:
            with suppress(OSError):
                self.conn.close()
            self.conn = None

    def shutdown(self) -> None:
        self.close()
        with suppress(OSError):
            self.socket.shutdown(socket.SHUT_RDWR)
        with suppress(OSError):
            self.socket.close()
