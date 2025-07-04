"""
$description Global live broadcasting and live broadcast archiving social platform.
$url twitcasting.tv
$type live
$metadata id
"""

import hashlib
import logging
import re
import sys

from streamlink.buffers import RingBuffer
from streamlink.plugin import Plugin, pluginargument, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.plugin.api.websocket import WebsocketClient
from streamlink.stream.hls import HLSStream, HLSStreamReader, HLSStreamWriter
from streamlink.stream.stream import Stream, StreamIO
from streamlink.utils.url import update_qsd


log = logging.getLogger(__name__)


class TwitCastingHLSStreamWriter(HLSStreamWriter):
    def should_filter_segment(self, segment):
        return "preroll-" in segment.uri or super().should_filter_segment(segment)


class TwitCastingHLSStreamReader(HLSStreamReader):
    __writer__ = TwitCastingHLSStreamWriter


class TwitCastingHLSStream(HLSStream):
    __reader__ = TwitCastingHLSStreamReader


@pluginmatcher(
    re.compile(r"https?://twitcasting\.tv/(?P<channel>[^/]+)"),
)
@pluginargument(
    "password",
    sensitive=True,
    metavar="PASSWORD",
    help="Password for private Twitcasting streams.",
)
class TwitCasting(Plugin):
    _URL_API_STREAMSERVER = "https://twitcasting.tv/streamserver.php"

    # prefer websocket streams over HLS streams due to latency reasons
    _WEIGHTS = {
        "ws_main": sys.maxsize,
        "ws_mobilesource": sys.maxsize - 1,
        "ws_base": sys.maxsize - 2,
        "hls_high": sys.maxsize - 10,
        "hls_medium": sys.maxsize - 11,
        "hls_low": sys.maxsize - 12,
    }

    @classmethod
    def stream_weight(cls, stream):
        return (cls._WEIGHTS[stream], "none") if stream in cls._WEIGHTS else super().stream_weight(stream)

    def _api_query_streamserver(self):
        return self.session.http.get(
            self._URL_API_STREAMSERVER,
            params={
                "target": self.match["channel"],
                "mode": "client",
                "player": "pc_web",
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    validate.optional("movie"): {
                        "id": int,
                        "live": bool,
                    },
                    validate.optional("llfmp4"): {
                        "streams": {
                            str: validate.url(),
                        },
                    },
                    validate.optional("tc-hls"): {
                        "streams": {
                            str: validate.url(),
                        },
                    },
                },
                validate.union_get("movie", "llfmp4", "tc-hls"),
            ),
        )

    def _get_streams_hls(self, streams, params=None):
        for name, url in streams.items():
            yield f"hls_{name}", TwitCastingHLSStream(self.session, url, params=params)

    def _get_streams_websocket(self, streams, params=None):
        for name, url in streams.items():
            yield f"ws_{name}", TwitCastingStream(self.session, url, params=params)

    def _get_streams(self):
        movie, websocket, hls = self._api_query_streamserver()
        if not movie or not movie.get("id") or not movie.get("live"):
            log.error(f"No live stream available for user {self.match['channel']}")
            return
        if not websocket and not hls:
            log.error("Unsupported stream type")
            return

        self.id = movie.get("id")

        params = {}
        if password := self.options.get("password"):
            params |= {"word": hashlib.md5(password.encode()).hexdigest()}

        if websocket:
            yield from self._get_streams_websocket(websocket["streams"], params)
        if hls:
            yield from self._get_streams_hls(hls["streams"], params)


class TwitCastingWsClient(WebsocketClient):
    def __init__(self, buffer: RingBuffer, *args, **kwargs):
        self.buffer = buffer
        super().__init__(*args, **kwargs)

    def on_close(self, *args, **kwargs):
        super().on_close(*args, **kwargs)
        self.buffer.close()

    def on_data(self, wsapp, data, data_type, cont):
        if data_type == self.OPCODE_TEXT:
            return

        try:
            self.buffer.write(data)
        except Exception as err:
            log.error(err)
            self.close()


class TwitCastingReader(StreamIO):
    def __init__(self, stream: "TwitCastingStream", timeout=None):
        super().__init__()
        self.session = stream.session
        self.stream = stream
        self.timeout = timeout or self.session.options.get("stream-timeout")

        buffer_size = self.session.get_option("ringbuffer-size")
        self.buffer = RingBuffer(buffer_size)

        self.wsclient = TwitCastingWsClient(
            self.buffer,
            stream.session,
            stream.url,
            origin="https://twitcasting.tv/",
        )

    def open(self):
        self.wsclient.start()

    def close(self):
        self.wsclient.close()
        self.buffer.close()

    def read(self, size):
        return self.buffer.read(
            size,
            block=self.wsclient.is_alive(),
            timeout=self.timeout,
        )


class TwitCastingStream(Stream):
    __shortname__ = "websocket"

    def __init__(self, session, url, params):
        super().__init__(session)
        self.url = update_qsd(url, params or {})

    def to_url(self):
        return self.url

    def open(self):
        reader = TwitCastingReader(self)
        reader.open()
        return reader


__plugin__ = TwitCasting
