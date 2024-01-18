"""
$description Chinese video sharing website based in Shanghai, themed around animation, comics, and games (ACG).
$url live.bilibili.com
$type live
"""

import logging
import re

from streamlink.exceptions import NoStreamsError
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream import HTTPStream
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(r"https?://live\.bilibili\.com/(?P<channel>[^/?#]+)"),
)
class Bilibili(Plugin):
    _URL_API_V1_PLAYURL = "https://api.live.bilibili.com/room/v1/Room/playUrl"
    _URL_API_V2_PLAYINFO = "https://api.live.bilibili.com/xlive/web-room/v2/index/getRoomPlayInfo"

    SHOW_STATUS_OFFLINE = 0
    SHOW_STATUS_ONLINE = 1
    SHOW_STATUS_ROUND = 2

    @classmethod
    def stream_weight(cls, stream):
        offset = 1 if "_alt" in stream else 0
        if stream.startswith("httpstream"):
            return 4 - offset, stream
        if stream.startswith("hls"):
            return 2 - offset, stream
        return super().stream_weight(stream)

    def _get_api_v1_playurl(self, room_id):
        return self.session.http.get(
            self._URL_API_V1_PLAYURL,
            params={
                "cid": room_id,
                "platform": "web",
                "quality": "4",
            },
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    validate.all(
                        {
                            "code": 0,
                            "data": {
                                "durl": [
                                    validate.all(
                                        {
                                            "url": validate.url(),
                                        },
                                        validate.get("url"),
                                    ),
                                ],
                            },
                        },
                        validate.get(("data", "durl")),
                    ),
                    validate.all(
                        {
                            "code": int,
                        },
                        validate.transform(lambda _: []),
                    ),
                ),
            ),
        )

    @property
    def _schema_v2_streams(self):
        return validate.all(
            [
                {
                    "protocol_name": str,
                    "format": validate.all(
                        [
                            {
                                "format_name": str,
                                "codec": validate.all(
                                    [
                                        {
                                            "codec_name": str,
                                            "base_url": str,
                                            "url_info": [
                                                {
                                                    "host": validate.url(),
                                                    "extra": str,
                                                },
                                            ],
                                        },
                                    ],
                                    validate.filter(lambda item: item["codec_name"] == "avc"),
                                ),
                            },
                        ],
                        validate.filter(lambda item: item["format_name"] in ("fmp4", "ts")),
                    ),
                },
            ],
            validate.filter(lambda item: item["protocol_name"] == "http_hls"),
        )

    def _get_api_v2_playinfo(self, room_id):
        return self.session.http.get(
            self._URL_API_V2_PLAYINFO,
            params={
                "room_id": room_id,
                "no_playurl": 0,
                "mask": 1,
                "qn": 0,
                "platform": "web",
                "protocol": "0,1",
                "format": "0,1,2",
                "codec": "0,1,2",
                "dolby": 5,
                "panorama": 1,
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "code": 0,
                    "data": {
                        "playurl_info": validate.none_or_all(
                            {
                                "playurl": {
                                    "stream": self._schema_v2_streams,
                                },
                            },
                            validate.get(("playurl", "stream")),
                        ),
                    },
                },
                validate.get(("data", "playurl_info")),
            ),
        )

    def _get_page_playinfo(self):
        data = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//script[contains(text(),'window.__NEPTUNE_IS_MY_WAIFU__={')][1]/text()"),
                validate.none_or_all(
                    validate.transform(str.replace, "window.__NEPTUNE_IS_MY_WAIFU__=", ""),
                    validate.parse_json(),
                    {
                        "roomInitRes": {
                            "data": {
                                "live_status": int,
                                "playurl_info": validate.none_or_all(
                                    {
                                        "playurl": {
                                            "stream": self._schema_v2_streams,
                                        },
                                    },
                                    validate.get(("playurl", "stream")),
                                ),
                            },
                        },
                        "roomInfoRes": {
                            "data": {
                                "room_info": {
                                    "live_id": int,
                                    "title": str,
                                    "area_name": str,
                                },
                                "anchor_info": {
                                    "base_info": {
                                        "uname": str,
                                    },
                                },
                            },
                        },
                    },
                    validate.union_get(
                        ("roomInfoRes", "data", "room_info", "live_id"),
                        ("roomInfoRes", "data", "anchor_info", "base_info", "uname"),
                        ("roomInfoRes", "data", "room_info", "area_name"),
                        ("roomInfoRes", "data", "room_info", "title"),
                        ("roomInitRes", "data", "live_status"),
                        ("roomInitRes", "data", "playurl_info"),
                    ),
                ),
            ),
        )
        if not data:
            return

        self.id, self.author, self.category, self.title, live_status, streams = data
        if live_status != self.SHOW_STATUS_ONLINE:
            log.info("Channel is offline")
            raise NoStreamsError

        return streams

    def _get_streams(self):
        http_streams = self._get_api_v1_playurl(self.match["channel"])
        for http_stream in http_streams:
            if self.session.http.head(http_stream, raise_for_status=False).status_code >= 400:
                continue
            yield "httpstream", HTTPStream(self.session, http_stream)

        hls_streams = self._get_page_playinfo()
        if not hls_streams:
            log.debug("Falling back to _get_api_v2_playinfo()")
            hls_streams = self._get_api_v2_playinfo(self.match["channel"])

        for hls_stream in hls_streams or []:
            for stream_format in hls_stream["format"]:
                for codec in stream_format["codec"]:
                    for url_info in codec["url_info"]:
                        url = f"{url_info['host']}{codec['base_url']}{url_info['extra']}"
                        yield "hls", HLSStream(self.session, url)


__plugin__ = Bilibili
