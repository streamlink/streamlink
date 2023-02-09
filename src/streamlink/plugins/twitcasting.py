"""
$description Global live broadcasting and live broadcast archiving social platform.
$url twitcasting.tv
$type live
"""

import hashlib
import logging
import re

from streamlink.buffers import RingBuffer
from streamlink.plugin import Plugin, PluginError, pluginargument, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.plugin.api.websocket import WebsocketClient
from streamlink.stream.stream import Stream, StreamIO
from streamlink.utils.url import update_qsd


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://twitcasting\.tv/(?P<channel>[^/]+)",
))
@pluginargument(
    "password",
    sensitive=True,
    metavar="PASSWORD",
    help="Password for private Twitcasting streams.",
)
class TwitCasting(Plugin):
    _STREAM_INFO_URL = "https://twitcasting.tv/streamserver.php?target={channel}&mode=client"
    _STREAM_REAL_URL = "{proto}://{host}/ws.app/stream/{movie_id}/fmp4/bd/1/1500?mode={mode}"

    _STREAM_INFO_SCHEMA = validate.Schema({
        validate.optional("movie"): {
            "id": int,
            "live": bool,
        },
        validate.optional("fmp4"): {
            "host": str,
            "proto": str,
            "source": bool,
            "mobilesource": bool,
        },
    })

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.channel = self.match.group("channel")

    def _get_streams(self):
        stream_info = self._get_stream_info()
        log.debug(f"Live stream info: {stream_info}")

        if not stream_info.get("movie") or not stream_info["movie"]["live"]:
            raise PluginError("The live stream is offline")

        if not stream_info.get("fmp4"):
            raise PluginError("Login required")

        # Keys are already validated by schema above
        proto = stream_info["fmp4"]["proto"]
        host = stream_info["fmp4"]["host"]
        movie_id = stream_info["movie"]["id"]

        if stream_info["fmp4"]["source"]:
            mode = "main"  # High quality
        elif stream_info["fmp4"]["mobilesource"]:
            mode = "mobilesource"  # Medium quality
        else:
            mode = "base"  # Low quality

        if (proto == "") or (host == "") or (not movie_id):
            raise PluginError(f"No stream available for user {self.channel}")

        real_stream_url = self._STREAM_REAL_URL.format(proto=proto, host=host, movie_id=movie_id, mode=mode)

        password = self.options.get("password")
        if password is not None:
            password_hash = hashlib.md5(password.encode()).hexdigest()
            real_stream_url = update_qsd(real_stream_url, {"word": password_hash})

        log.debug(f"Real stream url: {real_stream_url}")

        return {mode: TwitCastingStream(session=self.session, url=real_stream_url)}

    def _get_stream_info(self):
        url = self._STREAM_INFO_URL.format(channel=self.channel)
        res = self.session.http.get(url)
        return self.session.http.json(res, schema=self._STREAM_INFO_SCHEMA)


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
