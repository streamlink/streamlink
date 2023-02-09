"""
$description Live TV channels and video on-demand service from ZDF, a German public, independent broadcaster.
$url zdf.de
$type live, vod
$region Germany
"""

import logging
import re
from urllib.parse import urlparse, urlunparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.utils.url import url_concat


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(\w+\.)?(zdf\.de|3sat\.de)/",
))
class ZDFMediathek(Plugin):
    PLAYER_ID = "ngplayer_2_4"

    def _get_streams(self):
        zdf_json = self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string(".//*[@data-zdfplayer-jsb][1]/@data-zdfplayer-jsb"),
            validate.none_or_all(
                validate.parse_json(),
                {
                    "apiToken": str,
                    "content": validate.url(),
                },
                validate.union_get("apiToken", "content"),
            ),
        ))
        if zdf_json is None:
            return

        apiToken, apiUrl = zdf_json

        headers = {
            "Accept": "application/vnd.de.zdf.v1.0+json;charset=UTF-8",
            "Api-Auth": f"Bearer {apiToken}",
            "Referer": self.url,
        }

        pApiUrl = urlparse(apiUrl)
        apiUrlBase = urlunparse((pApiUrl.scheme, pApiUrl.netloc, "", "", "", ""))
        apiUrlPath = self.session.http.get(apiUrl, headers=headers, schema=validate.Schema(
            validate.parse_json(),
            {"mainVideoContent": {
                "http://zdf.de/rels/target": {
                    "http://zdf.de/rels/streams/ptmd-template": str,
                },
            }},
            validate.get(("mainVideoContent", "http://zdf.de/rels/target", "http://zdf.de/rels/streams/ptmd-template")),
            validate.transform(lambda template: template.format(playerId=self.PLAYER_ID).replace(" ", "")),
        ))

        stream_request_url = url_concat(apiUrlBase, apiUrlPath)
        data = self.session.http.get(stream_request_url, headers=headers, schema=validate.Schema(
            validate.parse_json(),
            {"priorityList": [{
                "formitaeten": validate.all(
                    [{
                        "type": str,
                        "qualities": validate.all(
                            [{
                                "quality": str,
                                "audio": {
                                    "tracks": [{
                                        "uri": validate.url(),
                                    }],
                                },
                            }],
                            validate.filter(lambda obj: obj["quality"] == "auto"),
                        ),
                    }],
                    validate.filter(lambda obj: obj["type"] == "h264_aac_ts_http_m3u8_http"),
                ),
            }]},
            validate.get("priorityList"),
        ))

        for priority in data:
            for formitaeten in priority["formitaeten"]:
                for quality in formitaeten["qualities"]:
                    for audio in quality["audio"]["tracks"]:
                        yield from HLSStream.parse_variant_playlist(self.session, audio["uri"], headers=headers).items()


__plugin__ = ZDFMediathek
