"""
$description Chinese video sharing website based in Shanghai, themed around animation, comics, and games (ACG).
$url live.bilibili.com
$type live
"""

import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(re.compile(
    r"https?://live\.bilibili\.com/(?P<channel>[^/]+)",
))
class Bilibili(Plugin):
    SHOW_STATUS_OFFLINE = 0
    SHOW_STATUS_ONLINE = 1
    SHOW_STATUS_ROUND = 2

    def _get_streams(self):
        schema_stream = validate.all(
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
                                "playurl_info": {
                                    "playurl": {
                                        "stream": schema_stream,
                                    },
                                },
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
                        ("roomInitRes", "data", "playurl_info", "playurl", "stream"),
                    ),
                ),
            ),
        )
        if not data:
            return

        self.id, self.author, self.category, self.title, live_status, streams = data
        if live_status != self.SHOW_STATUS_ONLINE:
            return

        for stream in streams:
            for stream_format in stream["format"]:
                for codec in stream_format["codec"]:
                    for url_info in codec["url_info"]:
                        url = f"{url_info['host']}{codec['base_url']}{url_info['extra']}"
                        yield "live", HLSStream(self.session, url)


__plugin__ = Bilibili
