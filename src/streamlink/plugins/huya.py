"""
$description Chinese live streaming platform for live video game broadcasts and individual live streams.
$url huya.com
$type live
"""

import base64
import logging
import re
from typing import Dict

from streamlink.compat import html_unescape
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.http import HTTPStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?huya\.com/(?P<channel>[^/]+)"
))
class Huya(Plugin):
    QUALITY_WEIGHTS = {}    # type: Dict[str, int]

    @classmethod
    def stream_weight(cls, key):
        weight = cls.QUALITY_WEIGHTS.get(key)
        if weight:
            return weight, "huya"

        return super(Huya, cls).stream_weight(key)

    def _get_streams(self):
        data = self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string(".//script[contains(text(),'var hyPlayerConfig = {')][1]/text()"),
            validate.any(None, validate.transform(
                re.compile(r"""(?P<q>"?)stream(?P=q)\s*:\s*(?:"(?P<base64>.+?)"|(?P<json>\{.+?})\s*}\s*;)""").search,
            )),
            validate.any(None, validate.all(
                validate.any(
                    validate.all(
                        validate.get("base64"),
                        validate.text,
                        validate.transform(base64.b64decode),
                    ),
                    validate.all(
                        validate.get("json"),
                        validate.text,
                    ),
                ),
                validate.parse_json(),
                {
                    "data": [{
                        "gameLiveInfo": {
                            "liveId": int,
                            "nick": validate.text,
                            "roomName": validate.text,
                        },
                        "gameStreamInfoList": [validate.all(
                            {
                                "sCdnType": validate.text,
                                "iPCPriorityRate": int,
                                "sStreamName": validate.text,
                                "sFlvUrl": validate.text,
                                "sFlvUrlSuffix": validate.text,
                                "sFlvAntiCode": validate.all(validate.text, validate.transform(lambda v: html_unescape(v))),
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
            )),
        ))
        if not data:
            return

        self.id, self.author, self.title, streamdata = data

        for cdntype, priority, streamname, flvurl, suffix, anticode in streamdata:
            name = "source_{}".format(cdntype.lower())
            self.QUALITY_WEIGHTS[name] = priority
            yield name, HTTPStream(self.session, "{0}/{1}.{2}?{3}".format(flvurl, streamname, suffix, anticode))

        log.debug("QUALITY_WEIGHTS: {0!r}".format(self.QUALITY_WEIGHTS))


__plugin__ = Huya
