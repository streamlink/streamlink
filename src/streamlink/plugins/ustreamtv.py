import re
from random import randint
from threading import Thread, Event

from streamlink.compat import urljoin
from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import useragents
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.stream import HTTPStream
from streamlink.stream.hls import HLSStreamReader


class UHSClient(object):
    API_URL = "http://r{0}-1-{1}-{2}-{3}.ums.ustream.tv"
    APP_ID, APP_VERSION = 2, 1
    api_schama = validate.Schema([{
        "args": [object],
        "cmd": validate.text
    }])
    connect_schama = validate.Schema([{
        "args": validate.all([{"host": validate.text, "connectionId": validate.text}], validate.length(1)),
        "cmd": "tracking"
    }], validate.length(1), validate.get(0), validate.get("args"), validate.get(0))
    module_info_schema = validate.Schema(
        [validate.get("stream")],
        validate.filter(lambda r: r is not None)
    )

    def __init__(self, session, media_id, application, **options):
        self.session = session
        http.headers.update({"User-Agent": useragents.IPHONE_6})
        self.logger = session.logger.new_module("plugin.ustream.apiclient")
        self.media_id = media_id
        self.application = application
        self.referrer = options.pop("referrer", None)
        self._host = None
        self.rsid = self.generate_rsid()
        self.rpin = self.generate_rpin()
        self._connection_id = None
        self._app_id = options.pop("app_id", self.APP_ID)
        self._app_version = options.pop("app_version", self.APP_VERSION)
        self._cluster = options.pop("cluster", "live")

    def connect(self, **options):
        result = self.send_command(type="viewer", appId=self._app_id,
                                   appVersion=self._app_version,
                                   rsid=self.rsid,
                                   rpin=self.rpin,
                                   referrer=self.referrer,
                                   media=str(self.media_id),
                                   application=self.application,
                                   schema=self.connect_schama)

        self._host = "http://{0}".format(result["host"])
        self._connection_id = result["connectionId"]
        self.logger.debug("Got new host={0}, and connectionId={1}", self._host, self._connection_id)
        return True

    def poll(self, schema=None):
        return self.send_command(connectionId=self._connection_id, schema=schema)

    def generate_rsid(self):
        return "{0:x}:{1:x}".format(randint(0, 1e10), randint(0, 1e10))

    def generate_rpin(self):
        return "_rpin.{0}".format(randint(0, 1e15))

    def send_command(self, schema=None, **args):
        res = http.get(self.host,
                       params=args,
                       headers={"Referer": self.referrer,
                                "User-Agent": useragents.IPHONE_6},
                       retries=5,
                       timeout=5.0)
        return http.json(res, schema=schema or self.api_schama)

    @property
    def host(self):
        host = self._host or self.API_URL.format(randint(0, 0xffffff), self.media_id, self.application,
                                                 "lp-" + self._cluster)
        return urljoin(host, "/1/ustream")


class UStreamHLSStream(HLSStream):
    class APIPoller(Thread):
        def __init__(self, api, interval=10.0):
            Thread.__init__(self)
            self.stopped = Event()
            self.api = api
            self.interval = interval

        def stop(self):
            self.stopped.set()

        def run(self):
            while not self.stopped.wait(self.interval):
                self.api.poll()

    def __init__(self, session_, url, api, force_restart=False, **args):
        super(UStreamHLSStream, self).__init__(session_, url, force_restart, **args)
        self.poller = self.APIPoller(api)
        self.poller.setDaemon(True)
        self.poller.start()

    def open(self):
        reader = HLSStreamReader(self)
        reader.open()
        return reader


class UStream(Plugin):
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

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _api_get_streams(self, media_id, application, cluster="live", referrer=None, retries=3):
        if retries > 0:
            app_id = 11
            app_ver = 2
            referrer = referrer or self.url
            self.api = UHSClient(self.session, media_id, application, referrer=referrer, cluster=cluster, app_id=app_id,
                                 app_version=app_ver)
            self.logger.debug("Connecting to UStream API: media_id={0}, application={1}, referrer={2}, cluster={3}, "
                              "app_id={4}, app_ver={5}",
                              media_id, application, referrer, cluster, app_id, app_ver)
            if self.api.connect():
                for i in range(5):  # make at most five requests to get the moduleInfo
                    for result in self.api.poll():
                        if result["cmd"] == "moduleInfo":
                            return self.handle_module_info(result["args"], media_id, application, cluster, referrer,
                                                           retries)
                        elif result["cmd"] == "reject":
                            return self.handle_reject(result["args"], media_id, application, cluster, referrer, retries)
                        else:
                            self.logger.debug("Unknown command: {0}", result["cmd"])
        return []

    def handle_module_info(self, args, media_id, application, cluster="live", referrer=None, retries=3):
        for streams in UHSClient.module_info_schema.validate(args):
            if isinstance(streams, list):
                for stream in streams:
                    for q, s in HLSStream.parse_variant_playlist(self.session, stream["url"]).items():
                        yield q, UStreamHLSStream(self.session, s.url, self.api)
            elif isinstance(streams, dict):
                for stream in streams.get("streams", []):
                    name = "{0}k".format(stream["bitrate"])
                    for surl in stream["streamName"]:
                        yield name, HTTPStream(self.session, surl)
            elif streams == "offline":
                self.logger.warning("This stream is currently offline")

    def handle_reject(self, args, media_id, application, cluster="live", referrer=None, retries=3):
        for arg in args:
            if "cluster" in arg:
                self.logger.debug("Switching cluster to {0}", arg["cluster"]["name"])
                cluster = arg["cluster"]["name"]
            if "referrerLock" in arg:
                referrer = arg["referrerLock"]["redirectUrl"]

        return self._api_get_streams(media_id,
                                     application,
                                     cluster=cluster,
                                     referrer=referrer,
                                     retries=retries - 1)

    def _get_streams(self):
        # establish a mobile non-websockets api connection
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
            media_id = self._find_media_id()

        if media_id:
            for s in self._api_get_streams(media_id, application):
                yield s
        else:
            self.logger.error("Cannot find a media_id on this page")

    def _find_media_id(self):
        self.logger.debug("Searching for media ID on the page")
        res = http.get(self.url, headers={"User-Agent": useragents.CHROME})
        m = self.media_id_re.search(res.text)
        return m and m.group(1)


__plugin__ = UStream
