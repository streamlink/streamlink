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
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://live\.bilibili\.com/(?P<channel>[^/]+)",
))
class Bilibili(Plugin):
    _URL_API_PLAYINFO = "https://api.live.bilibili.com/xlive/web-room/v2/index/getRoomPlayInfo"

    SHOW_STATUS_OFFLINE = 0
    SHOW_STATUS_ONLINE = 1
    SHOW_STATUS_ROUND = 2

    @staticmethod
    def _schema_streams():
        return validate.all(
            [{
                "protocol_name": str,
                "format": validate.all(
                    [{
                        "format_name": str,
                        "codec": validate.all(
                            [{
                                "codec_name": str,
                                "base_url": str,
                                "url_info": [{
                                    "host": validate.url(),
                                    "extra": str,
                                }],
                            }],
                            validate.filter(lambda item: item["codec_name"] == "avc"),
                        ),
                    }],
                    validate.filter(lambda item: item["format_name"] == "fmp4"),
                ),
            }],
            validate.filter(lambda item: item["protocol_name"] == "http_hls"),
        )

    def _get_api_playinfo(self, room_id):
        return self.session.http.get(
            self._URL_API_PLAYINFO,
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
                                    "stream": self._schema_streams(),
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
                                            "stream": self._schema_streams(),
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
        streams = self._get_page_playinfo()
        if not streams:
            log.debug("Falling back to _get_api_playinfo()")
            streams = self._get_api_playinfo(self.match["channel"])

        for stream in streams or []:
            for stream_format in stream["format"]:
                for codec in stream_format["codec"]:
                    for url_info in codec["url_info"]:
                        url = f"{url_info['host']}{codec['base_url']}{url_info['extra']}"
                        yield "live", HLSStream(self.session, url)


__plugin__ = Bilibili
