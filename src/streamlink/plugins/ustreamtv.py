from __future__ import print_function

import json
import re
from random import randint

import itertools

import time

from streamlink.compat import urljoin
from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import useragents
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.stream import HTTPStream


class UHSClient(object):
    WS_URL = "http://r{0}-1-{1}-{2}-{3}.ums.ustream.tv"
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
        validate.get("args"),
        [validate.get("stream")],
        validate.filter(lambda r: r is not None)
    )

    def __init__(self, session, media_id, application, **options):
        self.session = session
        http.headers.update({"User-Agent": useragents.IPHONE_6})
        self.logger = session.logger.new_module("plugin.ustream.apiclient")
        self.media_id = media_id
        self.application = application
        self.url = options.pop("url", None)
        self._host = None
        self.rsid = self.generate_rsid()
        self.rpin = self.generate_rpin()
        self._connection_id = None
        self._app_id = options.pop("app_id", self.APP_ID)
        self._app_version = options.pop("app_version", self.APP_VERSION)
        self._cluster = options.pop("cluster", "live")

    def connect(self, **options):
        options.pop("url", None)
        result = self.send_command(type="viewer", appId=self._app_id,
                                   appVersion=self._app_version,
                                   rsid=self.rsid,
                                   rpin=self.rpin,
                                   referrer=self.url or "unknown",
                                   media=str(self.media_id),
                                   application=self.application,
                                   schema=self.connect_schama)

        self._host = "http://{0}".format(result["host"])
        self._connection_id = result["connectionId"]
        self.logger.debug("Got new host={0}, and connectionId={1}", self._host, self._connection_id)
        return True

    def ping(self, schema=None):
        return self.send_command(connectionId=self._connection_id, schema=schema)

    def generate_rsid(self):
        return "{0:x}:{1:x}".format(randint(0, 1e10), randint(0, 1e10))

    def generate_rpin(self):
        return "_rpin.{0:x}".format(randint(0, 1e15))

    def send_command(self, schema=None, **args):
        res = http.get(self.host, params=args)
        return http.json(res, schema=schema or self.api_schama)

    @property
    def host(self):
        host = self._host or self.WS_URL.format(randint(0, 0xffffff), self.media_id, self.application, self._cluster)
        return urljoin(host, "/1/ustream")


class UStream(Plugin):
    url_re = re.compile(r"""
    https?://(www\.)?ustream\.tv
        (?:
            (/embed/|/channel/id/)(?P<channel_id>\d+)
        )?
        (?:
            /recorded/(?P<video_id>\d+)
        )?
    """, re.VERBOSE)
    media_id_re = re.compile(r'"ustream:channel_id"\s+content\s*=\s*"(\d+)"')

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _api_get_streams(self, media_id, application, cluster="live", retries=3):
        if retries > 0:
            app_id = 11 if application == "channel" else 2
            app_ver = 2 if application == "channel" else 3
            self.api = UHSClient(self.session, media_id, application, url=self.url, cluster=cluster, app_id=app_id, app_version=app_ver)
            if self.api.connect():
                for result in self.api.ping():
                    if result["cmd"] == "moduleInfo":
                        for stream in UHSClient.module_info_schema.validate(result):
                            for s in self._parse_module_stream(stream):
                                yield s
                    if result["cmd"] == "reject":
                        for s in self._api_get_streams(media_id,
                                                       application,
                                                       cluster=result["args"][0]["cluster"]["name"],
                                                       retries=retries-1):
                            yield s

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

    def _parse_module_stream(self, streams):
        if isinstance(streams, list):
            for stream in streams:
                for s in HLSStream.parse_variant_playlist(self.session, stream["url"]).items():
                    yield s
        elif isinstance(streams, dict):
            for stream in streams.get("streams", []):
                name = "{0}k".format(stream["bitrate"])
                for surl in stream["streamName"]:
                    yield name, HTTPStream(self.session, surl)
        elif streams == "offline":
            self.logger.warning("This stream is currently offline")


__plugin__ = UStream
