"""Plugin for NHK World, NHK Japan's english TV channel."""

import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HDSStream

API_URL = "http://api.sh.nhk.fivecool.tv/api/cdn/?publicId=3bz2huey&playerId=7Dy"

_url_re = re.compile("http(s)?://(\w+\.)?nhk.or.jp/nhkworld")
_schema = validate.Schema({
    "live-streams": [{
        "streams": validate.all(
            [{
                "protocol": validate.text,
                "streamUrl": validate.text
            }],
            validate.filter(lambda s: s["protocol"] in ("http-flash", "http-hds"))
        )
    }]
})


class NHKWorld(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        res = http.get(API_URL)
        data = http.json(res, schema=_schema)

        streams = {}
        for livestreams in data["live-streams"]:
            for stream in livestreams["streams"]:
                url = stream["streamUrl"]
                for name, stream in HDSStream.parse_manifest(self.session, url).items():
                    if name.endswith("k"):
                        streams[name] = stream

        return streams


__plugin__ = NHKWorld
