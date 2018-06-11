import json
import logging
import re
from random import randint
from threading import Thread, Event

import websocket

from streamlink.plugin import Plugin, PluginArguments, PluginArgument
from streamlink.plugin.api import useragents
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream, Stream
from streamlink.stream import HTTPStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)


class ModuleInfoNoStreams(Exception):
    pass


class UHSClient(object):
    """
    API Client, reverse engineered by observing the interactions
    between the web browser and the ustream servers.
    """
    API_URL = "ws://r{0}-1-{1}-{2}-ws-{3}.ums.ustream.tv:1935/1/ustream"
    APP_ID, APP_VERSION = 11, 2
    api_schama = validate.Schema({
        "args": [object],
        "cmd": validate.text
    })
    module_info_schema = validate.Schema(
        [validate.get("stream")],
        validate.filter(lambda r: r is not None)
    )

    def __init__(self, media_id, application, **options):
        http.headers.update({"User-Agent": useragents.IPHONE_6})
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

    def connect(self):
        log.debug("Connecting to {0}".format(self.host))
        self._ws = websocket.create_connection(self.host,
                                               header=["User-Agent: {0}".format(useragents.IPHONE_6)],
                                               origin="http://www.ustream.tv")

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
        data = parse_json(self._ws.recv(), schema=self.api_schama)
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


class UStreamWrapper(Stream):
    __shortname__ = "ustream"

    class APIPoller(Thread):
        """
        Poll the UStream API so that stream URLs stay valid, otherwise they expire after 30 seconds.
        """

        def __init__(self, api, interval=10.0):
            Thread.__init__(self)
            self.stopped = Event()
            self.api = api
            self.interval = interval

        def stop(self):
            log.debug("Stopping API polling...")
            self.stopped.set()

        def run(self):
            while not self.stopped.wait(1.0):
                cmd_args = self.api.recv()
                if not cmd_args:
                    continue
                log.debug("poll response: {0}".format(cmd_args))
                if cmd_args["cmd"] == "warning":
                    log.warning("{code}: {message}", **cmd_args["args"])
            log.debug("Stopped API polling")

        def stopper(self, f):
            def _stopper(*args, **kwargs):
                self.stop()
                return f(*args, **kwargs)
            return _stopper

    def __init__(self, session, stream, api):
        super(UStreamWrapper, self).__init__(session)
        self.stream = stream
        self.poller = self.APIPoller(api)
        self.poller.setDaemon(True)
        log.debug("Wrapping {0} stream".format(stream.shortname()))

    def open(self):
        self.poller.start()
        log.debug("Starting API polling thread")
        fd = self.stream.open()
        fd.close = self.poller.stopper(fd.close)
        return fd

    def __json__(self):
        return {"type": self.shortname(),
                "wrapped": self.stream.__json__()}


class UStreamTV(Plugin):
    url_re = re.compile(r"""
    https?://(www\.)?ustream\.tv
        (?:
            (/embed/|/channel/id/)(?P<channel_id>\d+)
        )?
        (?:
            (/embed)?/recorded/(?P<video_id>\d+)
        )?
    """, re.VERBOSE)
    media_id_re = re.compile(r'"ustream:channel_id"\s+content\s*=\s*"(\d+)"')
    arguments = PluginArguments(
        PluginArgument("password",
                       argument_name="ustream-password",
                       sensitive=True,
                       metavar="PASSWORD",
                       help="""
    A password to access password protected UStream.tv channels.
    """))

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def handle_module_info(self, api, args):
        res = {}
        for streams in api.module_info_schema.validate(args):
            if isinstance(streams, list):
                for stream in streams:
                    if stream['name'] == "uhls":
                        for q, s in HLSStream.parse_variant_playlist(self.session, stream["url"]).items():
                            res[q] = UStreamWrapper(self.session, s, api)
                    if stream['name'] == "ustream":
                        for substream in stream['streams']:
                            res["vod"] = HTTPStream(self.session, substream['streamName'])
            elif isinstance(streams, dict):
                for stream in streams.get("streams", []):
                    name = "{0}k".format(stream["bitrate"])
                    for surl in stream["streamName"]:
                        res[name] = HTTPStream(self.session, surl)
            elif streams == "offline":
                log.error("Stream is offline")
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

    def _get_streams(self):
        # establish a mobile non-websockets api connection
        media_id, application = self._get_media_app()
        if media_id:
            api = UHSClient(media_id, application, referrer=self.url, cluster="live", password=self.get_option("password"))
            log.debug("Connecting to UStream API: media_id={0}, application={1}, referrer={2}, cluster={3}",
                      media_id, application, self.url, "live")
            api.connect()
            for _ in range(5):
                data = api.recv()
                try:
                    if data["cmd"] == "moduleInfo":
                        r = self.handle_module_info(api, data["args"])
                        if r:
                            return r
                    elif data["cmd"] == "reject":
                        self.handle_reject(api, data["args"])
                    else:
                        log.debug("Unexpected `{0}` command".format(data["cmd"]))
                        log.trace("{0!r}".format(data))
                except ModuleInfoNoStreams:
                    return None

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
