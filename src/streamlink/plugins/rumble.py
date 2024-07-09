"""
$description Rumble is an online video platform founded in October 2013 by Chris Pavlovski as an alternative to YouTube for independent vloggers and smaller content creators.
$url rumble.com
$type live
$metadata id
$metadata author
$metadata title
"""

import logging
import re
from typing import Dict

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream, HTTPStream


log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(
        r"https?://rumble\.com/c/(?P<channel>[^/?]+)",
    ),
    name="channel",
)
@pluginmatcher(
    re.compile(
        r"https?://rumble\.com/(?P<room_id>[^/.]+)\.html",
    ),
    name="live",
)
class Rumble(Plugin):
    QUALITY_WEIGHTS: Dict[str, int] = {}

    _URL_WEB_LIVE = "https://rumble.com/c/{channel}/livestreams"
    _URL_API_LIVE_DETAIL = "https://rumble.com/embedJS/u3/"

    _PARAM_VER = 2
    _PARAM_REQUEST = "video"

    _SCHEMA_STREAM = {
        str: validate.all(
            {
                "url": validate.url(),
                "meta": {"bitrate": int},
            },
            validate.union_get("url", ("meta", "bitrate")),
        ),
    }

    @classmethod
    def stream_weight(cls, key):
        weight = cls.QUALITY_WEIGHTS.get(key)
        if weight:
            return weight, key

        return super().stream_weight(key)

    def _get_streams(self):
        if self.matches["channel"]:
            channel = self.match["channel"]
            live_uri = self.session.http.get(
                self._URL_WEB_LIVE.format(channel=channel),
                schema=validate.Schema(
                    validate.parse_html(),
                    validate.xml_xpath_string(
                        "/html/body/main/section/ol/div[1]/div[2][@class='videostream__footer videostream__footer--live']/a/@href",
                    ),
                ),
                timeout=5,
            )
            if not live_uri:
                return
            room_url = f"https://rumble.com{live_uri}"
        elif self.matches["live"]:
            room_url = self.url
        else:
            return
        embed_url = self.session.http.get(
            room_url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(
                    '//script[@type="application/ld+json"]',
                ),
                validate.parse_json(),
                list,
                validate.length(1),
                validate.get(0),
                {
                    "embedUrl": validate.url(),
                },
                validate.get("embedUrl"),
            ),
            timeout=5,
        )
        match = re.search(r"/embed/([^/]+)/$", embed_url)
        if not match:
            return
        self.id = match.group(1)
        live_detail = self.session.http.get(
            self._URL_API_LIVE_DETAIL,
            params={
                "v": self.id,
                "request": self._PARAM_REQUEST,
                "ver": self._PARAM_VER,
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "ua": {
                        validate.optional("hls"): validate.any(
                            {
                                "auto": {
                                    "url": validate.url(),
                                },
                            },
                            [],
                        ),
                        validate.optional("mp4"): validate.any(self._SCHEMA_STREAM, []),
                        validate.optional("webm"): validate.any(self._SCHEMA_STREAM, []),
                    },
                    "title": str,
                    "author": {"name": str},
                },
                validate.union_get(
                    ("ua", "hls"),
                    ("ua", "mp4"),
                    ("ua", "webm"),
                    "title",
                    ("author", "name"),
                ),
            ),
        )
        hls, mp4, webm, self.title, self.author = live_detail
        if hls:
            yield from HLSStream.parse_variant_playlist(self.session, hls.get("auto", {}).get("url", "")).items()
        elif mp4 or webm:
            streams = mp4 if mp4 else webm
            for name, (url, bitrate) in streams.items():
                self.QUALITY_WEIGHTS[name] = bitrate
                yield name, HTTPStream(self.session, url)


__plugin__ = Rumble
