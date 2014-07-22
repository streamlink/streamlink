import json
import os
import socket
import sys
import tempfile

from contextlib import contextmanager
from io import BytesIO

from .compat import is_win32, is_py3, shlex_quote

try:
    from BaseHTTPServer import BaseHTTPRequestHandler
except ImportError:
    from http.server import BaseHTTPRequestHandler


if is_win32:
    from ctypes import windll, cast, c_ulong, c_void_p, byref

    PIPE_ACCESS_OUTBOUND = 0x00000002
    PIPE_TYPE_BYTE = 0x00000000
    PIPE_READMODE_BYTE = 0x00000000
    PIPE_WAIT = 0x00000000
    PIPE_UNLIMITED_INSTANCES = 255
    INVALID_HANDLE_VALUE = -1


class NamedPipe(object):
    def __init__(self, name):
        self.fifo = None
        self.pipe = None

        if is_win32:
            self.path = os.path.join("\\\\.\\pipe", name)
            self.pipe = self._create_named_pipe(self.path)
        else:
            self.path = os.path.join(tempfile.gettempdir(), name)
            self._create_fifo(self.path)

    def _create_fifo(self, name):
        os.mkfifo(name, 0o660)

    def _create_named_pipe(self, path):
        bufsize = 8192

        if is_py3:
            create_named_pipe = windll.kernel32.CreateNamedPipeW
        else:
            create_named_pipe = windll.kernel32.CreateNamedPipeA

        pipe = create_named_pipe(path, PIPE_ACCESS_OUTBOUND,
                                 PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT,
                                 PIPE_UNLIMITED_INSTANCES,
                                 bufsize, bufsize,
                                 0, None)

        if pipe == INVALID_HANDLE_VALUE:
            error_code = windll.kernel32.GetLastError()
            raise IOError("Error code 0x{0:08X}".format(error_code))

        return pipe

    def open(self, mode):
        if not self.pipe:
            self.fifo = open(self.path, mode)

    def write(self, data):
        if self.pipe:
            windll.kernel32.ConnectNamedPipe(self.pipe, None)
            written = c_ulong(0)
            windll.kernel32.WriteFile(self.pipe, cast(data, c_void_p),
                                      len(data), byref(written),
                                      None)
            return written
        else:
            return self.fifo.write(data)

    def close(self):
        if self.pipe:
            windll.kernel32.DisconnectNamedPipe(self.pipe)
        else:
            self.fifo.close()
            os.unlink(self.path)


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "__json__"):
            return obj.__json__()
        elif isinstance(obj, bytes):
            return obj.decode("utf8", "ignore")
        else:
            return json.JSONEncoder.default(self, obj)


class HTTPRequest(BaseHTTPRequestHandler):
    def __init__(self, request_text):
        self.rfile = BytesIO(request_text)
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()

    def send_error(self, code, message):
        self.error_code = code
        self.error_message = message


class HTTPServer(object):
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn = self.host = self.port = None
        self.bound = False

    @property
    def url(self):
        return "http://{0}:{1}/".format(self.host, self.port)

    def bind(self, host="127.0.0.1", port=0):
        try:
            self.socket.bind((host, port))
        except socket.error as err:
            raise OSError(err)

        self.socket.listen(1)
        self.bound = True
        self.host, self.port = self.socket.getsockname()

    def open(self, timeout=30):
        self.socket.settimeout(timeout)

        try:
            conn, addr = self.socket.accept()
            conn.settimeout(None)
        except socket.timeout:
            raise OSError("Socket accept timed out")

        try:
            req_data = conn.recv(1024)
        except socket.error:
            raise OSError("Failed to read data from socket")

        req = HTTPRequest(req_data)

        conn.send(b"HTTP/1.1 200 OK\r\n")
        conn.send(b"Server: Livestreamer\r\n")
        conn.send(b"\r\n")
        self.conn = conn

        return req

    def write(self, data):
        if not self.conn:
            raise IOError("No connection")

        self.conn.sendall(data)

    def close(self, client_only=False):
        if self.conn:
            self.conn.close()

        if not client_only:
            self.socket.close()


@contextmanager
def ignored(*exceptions):
    try:
        yield
    except exceptions:
        pass


def check_paths(exes, paths):
    for path in paths:
        for exe in exes:
            path = os.path.join(path, exe)
            if os.path.isfile(path):
                return path


def find_default_player():
    if "darwin" in sys.platform:
        paths = os.environ.get("PATH", "").split(":")
        paths += ["/Applications/VLC.app/Contents/MacOS/"]
        paths += ["~/Applications/VLC.app/Contents/MacOS/"]
        path = check_paths(("VLC", "vlc"), paths)
    elif "win32" in sys.platform:
        exename = "vlc.exe"
        paths = os.environ.get("PATH", "").split(";")
        path = check_paths((exename,), paths)

        if not path:
            subpath = "VideoLAN\\VLC\\"
            envvars = ("PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432")
            paths = filter(None, (os.environ.get(var) for var in envvars))
            paths = (os.path.join(p, subpath) for p in paths)
            path = check_paths((exename,), paths)
    else:
        paths = os.environ.get("PATH", "").split(":")
        path = check_paths(("vlc",), paths)

    if path:
        # Quote command because it can contain space
        return shlex_quote(path)

def stream_to_url(stream):
    stream_type = type(stream).shortname()

    if stream_type in ("hls", "http"):
        url = stream.url

    elif stream_type == "rtmp":
        params = [stream.params.pop("rtmp", "")]
        stream_params = dict(stream.params)

        if "swfVfy" in stream.params:
            stream_params["swfUrl"] = stream.params["swfVfy"]
            stream_params["swfVfy"] = True

        if "swfhash" in stream.params:
            stream_params["swfVfy"] = True
            stream_params.pop("swfhash", None)
            stream_params.pop("swfsize", None)

        for key, value in stream_params.items():
            if isinstance(value, bool):
                value = str(int(value))

            # librtmp expects some characters to be escaped
            value = value.replace("\\", "\\5c")
            value = value.replace(" ", "\\20")
            value = value.replace('"', "\\22")

            params.append("{0}={1}".format(key, value))

        url = " ".join(params)

    else:
        url = None

    return url

__all__ = ["NamedPipe", "HTTPServer", "JSONEncoder", "ignored",
           "find_default_player", "stream_to_url"]
