"""
$description Chinese live-streaming platform for live video game broadcasts and individual live streams.
$url huya.com
$type live
"""

import base64
import logging
import re
from html import unescape as html_unescape
from typing import Dict

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.http import HTTPStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?huya\.com/(?P<channel>[^/]+)"
))
class Huya(Plugin):
    QUALITY_WEIGHTS: Dict[str, int] = {}

    @classmethod
    def stream_weight(cls, key):
        weight = cls.QUALITY_WEIGHTS.get(key)
        if weight:
            return weight, "huya"

        return super().stream_weight(key)

    def _get_streams(self):
        data = self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string(".//script[contains(text(),'var hyPlayerConfig = {')][1]/text()"),
            validate.none_or_all(
                re.compile(r"""(?P<q>"?)stream(?P=q)\s*:\s*(?:"(?P<base64>.+?)"|(?P<json>\{.+?})\s*}\s*;)"""),
            ),
            validate.none_or_all(
                validate.any(
                    validate.all(
                        validate.get("base64"),
                        str,
                        validate.transform(base64.b64decode),
                    ),
                    validate.all(
                        validate.get("json"),
                        str,
                    ),
                ),
                validate.parse_json(),
                {
                    "data": [{
                        "gameLiveInfo": {
                            "liveId": str,
                            "nick": str,
                            "roomName": str,
                        },
                        "gameStreamInfoList": [validate.all(
                            {
                                "sCdnType": str,
                                "iPCPriorityRate": int,
                                "sStreamName": str,
                                "sFlvUrl": str,
                                "sFlvUrlSuffix": str,
                                "sFlvAntiCode": validate.all(str, validate.transform(lambda v: html_unescape(v))),
                            },
                            validate.union_get(
                                "sCdnType",
                                "iPCPriorityRate",
                                "sStreamName",
                                "sFlvUrl",
                                "sFlvUrlSuffix",
                                "sFlvAntiCode",
                            )),
                        ],
                    }],
                },
                validate.get(("data", 0)),
                validate.union_get(
                    ("gameLiveInfo", "liveId"),
                    ("gameLiveInfo", "nick"),
                    ("gameLiveInfo", "roomName"),
                    "gameStreamInfoList",
                ),
            ),
        ))
        if not data:
            return

        self.id, self.author, self.title, streamdata = data

        for cdntype, priority, streamname, flvurl, suffix, anticode in streamdata:
            name = f"source_{cdntype.lower()}"
            self.QUALITY_WEIGHTS[name] = priority
            yield name, HTTPStream(self.session, f"{flvurl}/{streamname}.{suffix}?{anticode}")

        log.debug(f"QUALITY_WEIGHTS: {self.QUALITY_WEIGHTS!r}")


__plugin__ = Huya
