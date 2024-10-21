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
from time import time

from streamlink.buffers import RingBuffer
from streamlink.plugin import Plugin, pluginargument, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.plugin.api.websocket import WebsocketClient
from streamlink.stream.hls import HLSStream
from streamlink.stream.stream import Stream, StreamIO
from streamlink.utils.url import update_qsd


log = logging.getLogger(__name__)


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
    _URL_STREAM_HLS = "https://{host}/{channel}/metastream.m3u8"
    _URL_STREAM_WEBSOCKET = "wss://{host}/ws.app/stream/{id}/fmp4/bd/1/1500?mode={mode}"

    _STREAM_HOST_DEFAULT = "twitcasting.tv"

    _WEBSOCKET_MODES = {
        "main": "source",
        "mobilesource": "mobilesource",
        "base": None,
    }

    # prefer websocket streams over HLS streams due to latency reasons
    _WEIGHTS = {
        "main": sys.maxsize,
        "mobilesource": sys.maxsize - 1,
        "base": sys.maxsize - 2,
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
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    validate.optional("movie"): {
                        "id": int,
                        "live": bool,
                    },
                    # ignore llfmp4 websocket streams, as those seem to cause video/audio desync
                    validate.optional("fmp4"): {
                        "proto": str,
                        "host": str,
                        "source": bool,
                        "mobilesource": bool,
                    },
                    # ignore the "dvr" HLS URL, as it results in a 403 response
                    validate.optional("hls"): {
                        "host": str,
                        "proto": str,
                        "source": bool,
                    },
                },
                validate.union_get("movie", "fmp4", "hls"),
            ),
        )

    def _get_streams_hls(self, data):
        host = data.get("host") or self._STREAM_HOST_DEFAULT
        url = self._URL_STREAM_HLS.format(host=host, channel=self.match["channel"])
        params = {"__n": int(time() * 1000)}

        streams = [params]
        if data.get("source"):
            streams.append({"mode": "source", **params})

        for params in streams:
            yield from HLSStream.parse_variant_playlist(self.session, url, params=params).items()

    def _get_streams_websocket(self, data):
        host = data.get("host") or self._STREAM_HOST_DEFAULT
        password = self.options.get("password")

        for mode, prop in self._WEBSOCKET_MODES.items():
            if prop is not None and not data.get(prop):
                continue

            url = self._URL_STREAM_WEBSOCKET.format(host=host, id=self.id, mode=mode)
            if password is not None:
                password_hash = hashlib.md5(password.encode()).hexdigest()
                url = update_qsd(url, {"word": password_hash})

            yield mode, TwitCastingStream(self.session, url)

    def _get_streams(self):
        movie, websocket, hls = self._api_query_streamserver()
        if not movie or not movie.get("id") or not movie.get("live"):
            log.error(f"No live stream available for user {self.match['channel']}")
            return
        if not websocket and not hls:
            log.error("Unsupported stream type")
            return

        self.id = movie.get("id")

        if websocket:
            yield from self._get_streams_websocket(websocket)
        if hls:
            yield from self._get_streams_hls(hls)


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
    def __init__(self, session, url):
        super().__init__(session)
        self.url = url

    def to_url(self):
        return self.url

    def open(self):
        reader = TwitCastingReader(self)
        reader.open()
        return reader


__plugin__ = TwitCasting
