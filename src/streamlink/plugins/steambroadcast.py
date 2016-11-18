#!/usr/bin/env python
import logging

import re

import streamlink
from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.plugin.api.validate import Schema
from streamlink.stream.dash import DASHStream

log = logging.getLogger(__name__)


class SteamBroadcastPlugin(Plugin):
    _url_re = re.compile(r"http://steamcommunity.com/broadcast/watch/(\d+)")
    _get_broadcast_url = "http://steamcommunity.com/broadcast/getbroadcastmpd/"
    _user_agent = "streamlink/{}".format(streamlink.__version__)
    _broadcast_schema = Schema({
        "success": validate.any("ready", "unavailable"),
        "retry": int,
        "broadcastid": validate.any(validate.text, int),
        validate.optional("url"): validate.url(),
        validate.optional("viewertoken"): validate.text
    })

    def __init__(self, url):
        super(SteamBroadcastPlugin, self).__init__(url)

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_broadcast_stream(self, steamid, viewertoken=0):
        res = http.get(self._get_broadcast_url, params=dict(broadcastid=0,
                                                            steamid=steamid,
                                                            viewertoken=viewertoken))
        return http.json(res, schema=self._broadcast_schema)

    def _get_streams(self):
        # extract the steam ID from the URL
        steamid = self._url_re.match(self.url).group(1)

        streamdata = self._get_broadcast_stream(steamid)

        if streamdata[u"success"] == "ready":
            return DASHStream.parse_manifest(self.session, streamdata["url"])
        else:
            self.logger.error("This stream is currently unavailable")

__plugin__ = SteamBroadcastPlugin
