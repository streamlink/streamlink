from .compat import bytes, is_win32, urljoin
from .plugins import PluginError

from threading import Event, Lock

import argparse
import hashlib
import hmac
import os
import requests
import tempfile
import xml.dom.minidom
import zlib

if is_win32:
    from ctypes import windll, cast, c_ulong, c_void_p, byref

SWFKey = b"Genuine Adobe Flash Player 001"
RequestsConfig = { "danger_mode": True }

class ArgumentParser(argparse.ArgumentParser):
    def convert_arg_line_to_args(self, line):
        if len(line) == 0:
            return

        if line[0] == "#":
            return

        split = line.find("=")
        if split > 0:
            key = line[:split].strip()
            val = line[split+1:].strip()
            yield "--%s=%s" % (key, val)
        else:
            yield "--%s" % line

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
        PIPE_ACCESS_OUTBOUND = 0x00000002
        PIPE_TYPE_BYTE = 0x00000000
        PIPE_READMODE_BYTE = 0x00000000
        PIPE_WAIT = 0x00000000
        PIPE_UNLIMITED_INSTANCES = 255
        INVALID_HANDLE_VALUE = -1
        bufsize = 8192

        pipe = windll.kernel32.CreateNamedPipeA(path,
                                                PIPE_ACCESS_OUTBOUND,
                                                PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT,
                                                PIPE_UNLIMITED_INSTANCES,
                                                bufsize,
                                                bufsize,
                                                0,
                                                None)

        if pipe == INVALID_HANDLE_VALUE:
            raise IOError(("error code 0x{0:08X}").format(windll.kernel32.GetLastError()))

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
            os.unlink(self.path)

class Buffer(object):
    """ Simple buffer for use in single-threaded consumer/filler """

    def __init__(self):
        self.buffer = bytearray()
        self.closed = False

    def read(self, size=-1):
        if size < 0:
            size = len(self.buffer)

        data = self.buffer[:size]
        del self.buffer[:len(data)]

        return bytes(data)

    def write(self, data):
        if not self.closed:
            self.buffer.extend(data)

    def close(self):
        self.closed = True

    @property
    def length(self):
        return len(self.buffer)

class RingBuffer(Buffer):
    """ Circular buffer for use in multi-threaded consumer/filler """

    def __init__(self, size=8192*4):
        Buffer.__init__(self)

        self.buffer_size = size
        self.buffer_size_usable = size
        self.buffer_lock = Lock()

        self.event_free = Event()
        self.event_free.set()
        self.event_used = Event()

    def _read(self, size=-1):
        with self.buffer_lock:
            data = Buffer.read(self, size)

            if not self.is_full:
                self.event_free.set()

            if self.length == 0:
                self.event_used.clear()

        return data

    def read(self, size=-1, block=True, timeout=None):
        if block:
            self.event_used.wait(timeout)

            # If the event is still not set it's a timeout
            if not self.event_used.is_set() and self.length == 0:
                raise IOError("Read timeout")

        return self._read(size)

    def write(self, data):
        data_left = len(data)
        data_total = len(data)

        while data_left > 0:
            self.event_free.wait()

            if self.closed:
                return

            with self.buffer_lock:
                write_len = min(self.free, data_left)
                written = data_total - data_left

                Buffer.write(self, data[written:written+write_len])

                if self.length > 0:
                    self.event_used.set()

                if self.is_full:
                    self.event_free.clear()

                data_left -= write_len

    def wait_free(self, timeout=None):
        self.event_free.wait(timeout)

    def wait_used(self, timeout=None):
        self.event_used.wait(timeout)

    def close(self):
        Buffer.close(self)

        # Make sure we don't let a .write() and .read() block forever
        self.event_free.set()
        self.event_used.set()

    @property
    def free(self):
        return self.buffer_size - self.length

    @property
    def is_full(self):
        return self.free == 0


def urlopen(url, method="get", exception=PluginError, **args):
    if "data" in args and args["data"] is not None:
        method = "post"

    try:
        res = requests.request(method, url, config=RequestsConfig, timeout=15, **args)
    except (requests.exceptions.RequestException, IOError) as err:
        raise exception(("Unable to open URL: {url} ({err})").format(url=url, err=str(err)))

    return res

def urlget(url, prefetch=True, **args):
    return urlopen(url, method="get", prefetch=prefetch,
                   **args)

def urlresolve(url):
    res = urlget(url, prefetch=False, allow_redirects=False)

    if res.status_code == 302 and "location" in res.headers:
        return res.headers["location"]
    else:
        return url

def swfdecompress(data):
    if data[:3] == b"CWS":
        data = b"F" + data[1:8] + zlib.decompress(data[8:])

    return data

def swfverify(url):
    res = urlopen(url)
    swf = swfdecompress(res.content)

    h = hmac.new(SWFKey, swf, hashlib.sha256)

    return h.hexdigest(), len(swf)

def verifyjson(json, key):
    if not key in json:
        raise PluginError(("Missing '{0}' key in JSON").format(key))

    return json[key]

def absolute_url(baseurl, url):
    if not url.startswith("http"):
        return urljoin(baseurl, url)
    else:
        return url

def parsexml(data, xmltype="XML", exception=PluginError):
    try:
        dom = xml.dom.minidom.parseString(data)
    except Exception as err:
        if len(data) > 35:
            snippet = data[:35] + "..."
        else:
            snippet = data

        raise exception(("Unable to parse {0}: {1} ({2})").format(xmltype, err, snippet))

    return dom

def get_node_text(element):
    res = []
    for node in element.childNodes:
        if node.nodeType == node.TEXT_NODE:
            res.append(node.data)

    if len(res) == 0:
        return None
    else:
        return "".join(res)

__all__ = ["ArgumentParser", "NamedPipe", "Buffer", "RingBuffer",
           "urlopen", "urlget", "urlresolve", "swfdecompress",
           "swfverify", "verifyjson", "absolute_url", "parsexml",
           "get_node_text"]
