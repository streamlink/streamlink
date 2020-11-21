import logging
import re
from threading import Event, Thread
from urllib.parse import unquote_plus, urlparse

import websocket

from streamlink import logger
from streamlink.buffers import RingBuffer
from streamlink.plugin import Plugin, PluginError
from streamlink.plugin.api import useragents, validate
from streamlink.stream.stream import Stream
from streamlink.stream.stream import StreamIO

log = logging.getLogger(__name__)


class TwitCasting(Plugin):
    _url_re = re.compile(r"http(s)?://twitcasting.tv/(?P<channel>[^/]+)", re.VERBOSE)
    _STREAM_INFO_URL = "https://twitcasting.tv/streamserver.php?target={channel}&mode=client"
    _STREAM_REAL_URL = "{proto}://{host}/ws.app/stream/{movie_id}/fmp4/bd/1/1500?mode={mode}"

    _STREAM_INFO_SCHEMA = validate.Schema({
        "movie": {
            "id": int,
            "live": bool
        },
        "fmp4": {
            "host": validate.text,
            "proto": validate.text,
            "source": bool,
            "mobilesource": bool
        }
    })

    def __init__(self, url):
        Plugin.__init__(self, url)
        match = self._url_re.match(url).groupdict()
        self.channel = match.get("channel")
        self.session.http.headers.update({'User-Agent': useragents.CHROME})

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        stream_info = self._get_stream_info()
        log.debug("Live stream info: {}".format(stream_info))

        if not stream_info["movie"]["live"]:
            raise PluginError("The live stream is offline")

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

        if (proto == '') or (host == '') or (not movie_id):
            raise PluginError("No stream available for user {}".format(self.channel))

        real_stream_url = self._STREAM_REAL_URL.format(proto=proto, host=host, movie_id=movie_id, mode=mode)
        log.debug("Real stream url: {}".format(real_stream_url))

        return {mode: TwitCastingStream(session=self.session, url=real_stream_url)}

    def _get_stream_info(self):
        url = self._STREAM_INFO_URL.format(channel=self.channel)
        res = self.session.http.get(url)
        return self.session.http.json(res, schema=self._STREAM_INFO_SCHEMA)


class TwitCastingWsClient(Thread):
    """
    Recieve stream data from TwitCasting server via WebSocket.
    """
    def __init__(self, url, buffer, proxy=""):
        Thread.__init__(self)
        self.stopped = Event()
        self.url = url
        self.buffer = buffer
        self.proxy = proxy
        self.ws = None

    @staticmethod
    def parse_proxy_url(purl):
        """
        Credit: streamlink/plugins/ustreamtv.py:UHSClient:parse_proxy_url()
        """
        proxy_options = {}
        if purl:
            p = urlparse(purl)
            proxy_options['proxy_type'] = p.scheme
            proxy_options['http_proxy_host'] = p.hostname
            if p.port:
                proxy_options['http_proxy_port'] = p.port
            if p.username:
                proxy_options['http_proxy_auth'] = (unquote_plus(p.username), unquote_plus(p.password or ""))
        return proxy_options

    def stop(self):
        if not self.stopped.wait(0):
            log.debug("Stopping WebSocket client...")
            self.stopped.set()
            self.ws.close()

    def run(self):
        if self.stopped.wait(0):
            return

        def on_message(ws, data):
            if not self.stopped.wait(0):
                try:
                    self.buffer.write(data)
                except Exception as err:
                    log.error(err)
                    self.stop()

        def on_error(ws, error):
            log.error(error)

        def on_close(ws):
            log.debug("Disconnected from WebSocket server")

        # Parse proxy string for websocket-client
        proxy_options = self.parse_proxy_url(self.proxy)
        if proxy_options.get('http_proxy_host'):
            log.debug("Connecting to {0} via proxy ({1}://{2}:{3})".format(
                self.url,
                proxy_options.get('proxy_type') or "http",
                proxy_options.get('http_proxy_host'),
                proxy_options.get('http_proxy_port') or 80
            ))
        else:
            log.debug("Connecting to {0} without proxy".format(self.url))

        # Connect to WebSocket server
        self.ws = websocket.WebSocketApp(
            self.url,
            header=["User-Agent: {0}".format(useragents.CHROME)],
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        self.ws.run_forever(origin="https://twitcasting.tv/", **proxy_options)


class TwitCastingReader(StreamIO):
    def __init__(self, stream, timeout=None, **kwargs):
        StreamIO.__init__(self)
        self.stream = stream
        self.session = stream.session
        self.timeout = timeout if timeout else self.session.options.get("stream-timeout")
        self.buffer = None

        if logger.root.level <= logger.DEBUG:
            websocket.enableTrace(True, log)

    def open(self):
        # Prepare buffer
        buffer_size = self.session.get_option("ringbuffer-size")
        self.buffer = RingBuffer(buffer_size)

        log.debug("Starting WebSocket client")
        self.client = TwitCastingWsClient(
            self.stream.url,
            buffer=self.buffer,
            proxy=self.session.get_option("http-proxy")
        )
        self.client.setDaemon(True)
        self.client.start()

    def close(self):
        self.client.stop()
        self.buffer.close()

    def read(self, size):
        if not self.buffer:
            return b""

        return self.buffer.read(size, block=(not self.client.stopped.wait(0)),
                                timeout=self.timeout)


class TwitCastingStream(Stream):
    def __init__(self, session, url):
        super().__init__(session)
        self.url = url

    def __repr__(self):
        return "<TwitCastingStream({0!r})>".format(self.url)

    def open(self):
        reader = TwitCastingReader(self)
        reader.open()
        return reader


__plugin__ = TwitCasting
