"""Plugin for TV4 Play, swedish TV channel TV4's streaming service."""

import re

from streamlink.compat import urlparse
from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HDSStream, RTMPStream

ASSET_URL = "http://prima.tv4play.se/api/web/asset/{0}/play"
SWF_URL = "http://www.tv4play.se/flash/tv4video.swf"

_url_re = re.compile("""
    http(s)?://(www\.)?
    (?:
        tv4play.se/program/[^\?/]+
    )?
    (?:
        fotbollskanalen.se/video
    )?
    .+(video_id|videoid)=(?P<video_id>\d+)
""", re.VERBOSE)

_asset_schema = validate.Schema(
    validate.xml_findall("items/item"),
    [
        validate.all(
            validate.xml_findall("*"),
            validate.map(lambda e: (e.tag, e.text)),
            validate.transform(dict),
            {
                "base": validate.text,
                "bitrate": validate.all(
                    validate.text, validate.transform(int)
                ),
                "url": validate.text
            }
        )
    ]
)


class TV4Play(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        video_id = match.group("video_id")
        res = http.get(ASSET_URL.format(video_id))
        assets = http.xml(res, schema=_asset_schema)

        streams = {}
        for asset in assets:
            base = asset["base"]
            url = asset["url"]

            if urlparse(url).path.endswith(".f4m"):
                streams.update(
                    HDSStream.parse_manifest(self.session, url, pvswf=SWF_URL)
                )
            elif base.startswith("rtmp"):
                name = "{0}k".format(asset["bitrate"])
                params = {
                    "rtmp": asset["base"],
                    "playpath": url,
                    "live": True
                }
                streams[name] = RTMPStream(self.session, params)

        return streams

__plugin__ = TV4Play
