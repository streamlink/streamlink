import datetime
import errno
import json
import logging
import re
from collections import deque, namedtuple
from random import randint
from socket import error as SocketError
from threading import Event, Thread
from time import sleep
from urllib.parse import unquote_plus, urljoin, urlparse, urlunparse

import websocket

from streamlink.exceptions import PluginError, StreamError
from streamlink.plugin import Plugin, PluginArgument, PluginArguments
from streamlink.plugin.api import useragents, validate
from streamlink.stream.dash_manifest import sleep_until, utc
from streamlink.stream.flvconcat import FLVTagConcat
from streamlink.stream.segmented import (SegmentedStreamReader, SegmentedStreamWorker, SegmentedStreamWriter)
from streamlink.stream.stream import Stream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)

Chunk = namedtuple("Chunk", "num url available_at")
ChunkData = namedtuple("ChunkData", "chunk_id chunk_time hashes current_timestamp")


class ModuleInfoNoStreams(Exception):
    pass


class UHSClient:
    """
    API Client, reverse engineered by observing the interactions
    between the web browser and the ustream servers.
    """
    API_URL = "ws://r{0}-1-{1}-{2}-ws-{3}.ums.ustream.tv:1935/1/ustream"
    APP_ID, APP_VERSION = 3, 2
    api_schema = validate.Schema({
        "args": [object],
        "cmd": validate.text
    })

    def __init__(self, media_id, application, **options):
        self.media_id = media_id
        self.application = application
        self._referrer = options.pop("referrer", None)
        self._host = None
        self.rsid = self.generate_rsid()
        self.rpin = self.generate_rpin()
        self._connection_id = None
        self._app_id = options.pop("app_id", self.APP_ID)
        self._app_version = options.pop("app_version", self.APP_VERSION)
        self._cluster = options.pop("cluster", "live")
        self._password = options.pop("password")
        self._proxy_url = options.pop("proxy")
        self._ws = None

    @property
    def referrer(self):
        return self._referrer

    @referrer.setter
    def referrer(self, referrer):
        log.info("Updating referrer to: {0}".format(referrer))
        self._referrer = referrer
        self.reconnect()

    @property
    def cluster(self):
        return self._cluster

    @cluster.setter
    def cluster(self, cluster):
        log.info("Switching cluster to: {0}".format(cluster))
        self._cluster = cluster
        self.reconnect()

    @staticmethod
    def parse_proxy_url(purl):
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

    def connect(self):
        proxy_options = self.parse_proxy_url(self._proxy_url)
        if proxy_options.get('http_proxy_host'):
            log.debug("Connecting to {0} via proxy ({1}://{2}:{3})".format(self.host,
                                                                           proxy_options.get('proxy_type') or "http",
                                                                           proxy_options.get('http_proxy_host'),
                                                                           proxy_options.get('http_proxy_port') or 80))
        else:
            log.debug("Connecting to {0}".format(self.host))
        self._ws = websocket.create_connection(self.host,
                                               header=["User-Agent: {0}".format(useragents.CHROME)],
                                               origin="https://www.ustream.tv",
                                               **proxy_options)

        args = dict(type="viewer",
                    appId=self._app_id,
                    appVersion=self._app_version,
                    rsid=self.rsid,
                    rpin=self.rpin,
                    referrer=self._referrer,
                    clusterHost="r%rnd%-1-%mediaId%-%mediaType%-%protocolPrefix%-%cluster%.ums.ustream.tv",
                    media=str(self.media_id),
                    application=self.application)
        if self._password:
            args["password"] = self._password

        result = self.send("connect", **args)
        return result > 0

    def reconnect(self):
        log.debug("Reconnecting...")
        if self._ws:
            self._ws.close()
        return self.connect()

    def generate_rsid(self):
        return "{0:x}:{1:x}".format(randint(0, 1e10), randint(0, 1e10))

    def generate_rpin(self):
        return "_rpin.{0}".format(randint(0, 1e15))

    def send(self, command, **args):
        log.debug("Sending `{0}` command".format(command))
        log.trace("{0!r}".format({"cmd": command, "args": [args]}))
        return self._ws.send(json.dumps({"cmd": command, "args": [args]}))

    def recv(self):
        data = parse_json(self._ws.recv(), schema=self.api_schema)
        log.debug("Received `{0}` command".format(data["cmd"]))
        log.trace("{0!r}".format(data))
        return data

    def disconnect(self):
        if self._ws:
            log.debug("Disconnecting...")
            self._ws.close()
            self._ws = None

    @property
    def host(self):
        return self._host or self.API_URL.format(randint(0, 0xffffff), self.media_id, self.application, self._cluster)


class UHSStreamWriter(SegmentedStreamWriter):
    def __init__(self, *args, **kwargs):
        SegmentedStreamWriter.__init__(self, *args, **kwargs)

        self.concater = FLVTagConcat(tags=[],
                                     flatten_timestamps=True,
                                     sync_headers=True)

    def fetch(self, chunk, retries=None):
        if not retries or self.closed:
            return

        try:
            now = datetime.datetime.now(tz=utc)
            if chunk.available_at > now:
                time_to_wait = (chunk.available_at - now).total_seconds()
                log.debug("Waiting for chunk: {fname} ({wait:.01f}s)".format(fname=chunk.num,
                                                                             wait=time_to_wait))
                sleep_until(chunk.available_at)

            return self.session.http.get(chunk.url,
                                         timeout=self.timeout,
                                         exception=StreamError)
        except StreamError as err:
            log.error(f"Failed to open chunk {chunk.num}: {err}")
            return self.fetch(chunk, retries - 1)

    def write(self, chunk, res, chunk_size=8192):
        try:
            for data in self.concater.iter_chunks(buf=res.content,
                                                  skip_header=False):
                self.reader.buffer.write(data)
                if self.closed:
                    return
            else:
                log.debug(f"Download of chunk {chunk.num} complete")
        except OSError as err:
            log.error(f"Failed to read chunk {chunk.num}: {err}")


class UHSStreamWorker(SegmentedStreamWorker):
    def __init__(self, *args, **kwargs):
        SegmentedStreamWorker.__init__(self, *args, **kwargs)
        self.chunks = []
        self.chunks_reload_time = 5

        self.chunk_id = self.stream.first_chunk_data.chunk_id
        self.template_url = self.stream.template_url

        self.process_chunks()
        if self.chunks:
            log.debug(f"First Chunk: {self.chunks[0].num}; Last Chunk: {self.chunks[-1].num}")

    def process_chunks(self):
        chunk_data = []
        if self.chunk_id == self.stream.first_chunk_data.chunk_id:
            chunk_data = self.stream.first_chunk_data
        elif self.stream.poller.data_chunks:
            chunk_data = self.stream.poller.data_chunks.popleft()

        if chunk_data:
            chunks = []
            count = 0
            for k, v in sorted(chunk_data.hashes.items(),
                               key=lambda c: int(c[0])):
                start = int(k)
                end = int(k) + 10
                for i in range(start, end):
                    if i > chunk_data.chunk_id and chunk_data.chunk_id != 0:
                        # Live: id is higher as chunk_data.chunk_id
                        count += chunk_data.chunk_time / 1000
                        available_at = (chunk_data.current_timestamp
                                        + datetime.timedelta(seconds=count))
                    else:
                        # Live: id is the same as chunk_data.chunk_id or lower
                        # VOD: chunk_data.chunk_id is 0
                        available_at = chunk_data.current_timestamp
                    chunks += [Chunk(int(i),
                                     self.template_url % (int(i), v),
                                     available_at)]
            self.chunks = chunks

    def valid_chunk(self, chunk):
        return chunk.num >= self.chunk_id

    def iter_segments(self):
        while not self.closed:
            for chunk in filter(self.valid_chunk, self.chunks):
                log.debug(f"Adding chunk {chunk.num} to queue")
                yield chunk
                # End of stream
                if self.closed:
                    return

                self.chunk_id = int(chunk.num) + 1

            if self.wait(self.chunks_reload_time):
                try:
                    self.process_chunks()
                except StreamError as err:
                    log.warning(f"Failed to process module info: {err}")


class UHSStreamReader(SegmentedStreamReader):
    __worker__ = UHSStreamWorker
    __writer__ = UHSStreamWriter

    def __init__(self, stream, *args, **kwargs):
        SegmentedStreamReader.__init__(self, stream, *args, **kwargs)


class UHSStream(Stream):
    __shortname__ = "uhs"

    class APIPoller(Thread):
        """
        Poll the UStream API.
        """

        def __init__(self, api, interval=10.0):
            Thread.__init__(self)
            self.stopped = Event()
            self.api = api
            self.interval = interval
            self.data_chunks = deque()

        def stop(self):
            log.debug("Stopping API polling...")
            self.stopped.set()

        def run(self):
            while not self.stopped.wait(0):
                try:
                    cmd_args = self.api.recv()
                except (SocketError,
                        websocket._exceptions.WebSocketConnectionClosedException) as err:
                    cmd_args = None
                    if (hasattr(err, "errno") and err.errno in (errno.ECONNRESET, errno.ETIMEDOUT)
                            or "Connection is already closed." in str(err)):
                        while True:
                            # --stream-timeout will handle the timeout
                            try:
                                # reconnect on network issues
                                self.api.reconnect()
                                break
                            except websocket._exceptions.WebSocketAddressException:
                                # no connection available
                                reconnect_time_ws = 5
                                log.error("Local network issue, websocket reconnecting in {0}s".format(reconnect_time_ws))
                                sleep(reconnect_time_ws)
                    else:
                        raise
                except PluginError:
                    continue

                if not cmd_args:
                    continue
                if cmd_args["cmd"] == "warning":
                    log.warning(f"{cmd_args['args']['code']}: {cmd_args['args']['message']}")
                if cmd_args["cmd"] == "moduleInfo":
                    data = self.handle_module_info(cmd_args["args"])
                    if data:
                        self.data_chunks.append(data)
            log.debug("Stopped API polling")

        def stopper(self, f):
            def _stopper(*args, **kwargs):
                self.stop()
                return f(*args, **kwargs)

            return _stopper

        def handle_module_info(self, args):
            for arg in args:
                if "stream" in arg and bool(arg["stream"].get("streamFormats")):
                    flv_segmented = arg["stream"]["streamFormats"]["flv/segmented"]
                    return ChunkData(flv_segmented["chunkId"],
                                     flv_segmented["chunkTime"],
                                     flv_segmented["hashes"],
                                     datetime.datetime.now(tz=utc))

    def __init__(self, session, api, first_chunk_data, template_url):
        super().__init__(session)
        self.session = session
        self.poller = self.APIPoller(api)
        self.poller.setDaemon(True)

        self.first_chunk_data = first_chunk_data
        self.template_url = template_url

    def open(self):
        self.poller.start()
        log.debug("Starting API polling thread")
        reader = UHSStreamReader(self)
        reader.open()
        reader.close = self.poller.stopper(reader.close)

        return reader


class UStreamTV(Plugin):
    url_re = re.compile(r"""(?x)
    https?://(?:(www\.)?ustream\.tv|video\.ibm\.com)
        (?:
            (/embed/|/channel/id/)(?P<channel_id>\d+)
        )?
        (?:
            (/embed)?/recorded/(?P<video_id>\d+)
        )?
    """)
    media_id_re = re.compile(r'"ustream:channel_id"\s+content\s*=\s*"(\d+)"')
    arguments = PluginArguments(
        PluginArgument("password",
                       argument_name="ustream-password",
                       sensitive=True,
                       metavar="PASSWORD",
                       help="""
    A password to access password protected UStream.tv channels.
    """))

    STREAM_WEIGHTS = {
        "original": 65535,
    }

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    @classmethod
    def stream_weight(cls, stream):
        if stream in cls.STREAM_WEIGHTS:
            return cls.STREAM_WEIGHTS[stream], "ustreamtv"
        return Plugin.stream_weight(stream)

    def handle_module_info(self, args):
        res = {}
        for arg in args:
            if "cdnConfig" in arg:
                parts = [
                    # scheme
                    arg["cdnConfig"]["protocol"],
                    # netloc
                    arg["cdnConfig"]["data"][0]["data"][0]["sites"][0]["host"],
                    # path
                    arg["cdnConfig"]["data"][0]["data"][0]["sites"][0]["path"],
                    "", "", "",  # params, query, fragment
                ]
                # Example:
                # LIVE: http://uhs-akamai.ustream.tv/
                # VOD:  http://vod-cdn.ustream.tv/
                res["cdn_url"] = urlunparse(parts)
            if "stream" in arg and bool(arg["stream"].get("streamFormats")):
                data = arg["stream"]
                if data["streamFormats"].get("flv/segmented"):
                    flv_segmented = data["streamFormats"]["flv/segmented"]
                    path = flv_segmented["contentAccess"]["accessList"][0]["data"]["path"]

                    res["streams"] = []
                    for stream in flv_segmented["streams"]:
                        res["streams"] += [dict(
                            stream_name="{0}p".format(stream["videoCodec"]["height"]),
                            path=urljoin(path,
                                         stream["segmentUrl"].replace("%", "%s")),
                            hashes=flv_segmented["hashes"],
                            first_chunk=flv_segmented["chunkId"],
                            chunk_time=flv_segmented["chunkTime"],
                        )]
                elif bool(data["streamFormats"]):
                    # supported formats:
                    # - flv/segmented
                    # unsupported formats:
                    # - flv
                    # - mp4
                    # - mp4/segmented
                    raise PluginError("Stream format is not supported: {0}".format(
                        ", ".join(data["streamFormats"].keys())))
            elif "stream" in arg and arg["stream"]["contentAvailable"] is False:
                log.error("This stream is currently offline")
                raise ModuleInfoNoStreams

        return res

    def handle_reject(self, api, args):
        for arg in args:
            if "cluster" in arg:
                api.cluster = arg["cluster"]["name"]
            if "referrerLock" in arg:
                api.referrer = arg["referrerLock"]["redirectUrl"]
            if "nonexistent" in arg:
                log.error("This channel does not exist")
                raise ModuleInfoNoStreams
            if "geoLock" in arg:
                log.error("This content is not available in your area")
                raise ModuleInfoNoStreams

    def _get_streams(self):
        media_id, application = self._get_media_app()
        if media_id:
            api = UHSClient(media_id, application,
                            referrer=self.url,
                            cluster="live",
                            password=self.get_option("password"),
                            proxy=self.session.get_option("http-proxy"))
            log.debug(f"Connecting to UStream API: "
                      f"media_id={media_id}, application={application}, referrer={self.url}, cluster=live")
            api.connect()

            streams_data = {}
            for _ in range(5):
                # do not use to many tries, it might take longer for a timeout
                # when streamFormats is {} and contentAvailable is True
                data = api.recv()
                try:
                    if data["cmd"] == "moduleInfo":
                        r = self.handle_module_info(data["args"])
                        if r:
                            streams_data.update(r)
                    elif data["cmd"] == "reject":
                        self.handle_reject(api, data["args"])
                    else:
                        log.debug("Unexpected `{0}` command".format(data["cmd"]))
                        log.trace("{0!r}".format(data))
                except ModuleInfoNoStreams:
                    break

                if streams_data.get("streams") and streams_data.get("cdn_url"):
                    for s in sorted(streams_data["streams"],
                                    key=lambda k: (k["stream_name"], k["path"])):
                        yield s["stream_name"], UHSStream(
                            session=self.session,
                            api=api,
                            first_chunk_data=ChunkData(
                                s["first_chunk"],
                                s["chunk_time"],
                                s["hashes"],
                                datetime.datetime.now(tz=utc)),
                            template_url=urljoin(streams_data["cdn_url"],
                                                 s["path"]),
                        )
                    break

    def _get_media_app(self):
        umatch = self.url_re.match(self.url)
        application = "channel"

        channel_id = umatch.group("channel_id")
        video_id = umatch.group("video_id")
        if channel_id:
            application = "channel"
            media_id = channel_id
        elif video_id:
            application = "recorded"
            media_id = video_id
        else:
            res = self.session.http.get(self.url, headers={"User-Agent": useragents.CHROME})
            m = self.media_id_re.search(res.text)
            media_id = m and m.group(1)
        return media_id, application


__plugin__ = UStreamTV
