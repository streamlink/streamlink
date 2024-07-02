"""
$description Chinese live-streaming platform for live video game broadcasts and individual live streams.
$url huya.com
$type live
$metadata id
$metadata author
$metadata title
"""

import base64
import hashlib
import logging
import random
import re
import time
from html import unescape as html_unescape
from typing import Dict
from urllib.parse import parse_qsl, unquote

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.http import HTTPStream
from streamlink.utils.url import update_qsd, update_scheme

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?huya\.com/(?P<channel>[^/?]+)",
))
class Huya(Plugin):
    QUALITY_WEIGHTS: Dict[str, int] = {}

    _QUALITY_WEIGHTS_OVERRIDE = {
        "source_hy": -1000,  # SSLCertVerificationError
    }
    _STREAM_URL_QUERYSTRING_PARAMS = "wsSecret", "wsTime", "fm", "ctype", "fs"

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
                                "sFlvAntiCode": validate.all(str, validate.transform(html_unescape)),
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
                    "vMultiStreamInfo": [
                        {
                            'sDisplayName': str,
                            'iBitRate': int
                        }
                    ]
                },
                validate.union_get(
                    ('data', 0, "gameLiveInfo", "liveId"),
                    ('data', 0, "gameLiveInfo", "nick"),
                    ('data', 0, "gameLiveInfo", "roomName"),
                    ('data', 0, "gameStreamInfoList"),
                    'vMultiStreamInfo'
                ),
            ),
        ))
        if not data:
            return

        self.id, self.author, self.title, streamdata, vMultiStreamInfo = data

        self.session.http.headers.update({
            "Origin": "https://www.huya.com",
            "Referer": "https://www.huya.com/",
        })

        for cdntype, priority, streamname, flvurl, suffix, anticode in streamdata:
            for q in vMultiStreamInfo:
                iBitRate = q['iBitRate']
                qs = {k: v for k, v in dict(parse_qsl(anticode)).items() if k in self._STREAM_URL_QUERYSTRING_PARAMS}
                fm = qs['fm']
                ctype = qs['ctype']
                platform_id = 100
                uid = random.randint(12340000, 12349999)
                convert_uid = (uid << 8 | uid >> (32 - 8)) & 0xFFFFFFFF
                wsTime = qs['wsTime']
                seqid = uid + int(time.time() * 1000)
                ws_secret_prefix = base64.b64decode(unquote(fm).encode()).decode().split("_")[0]
                ws_secret_hash = hashlib.md5(f'{seqid}|{ctype}|{platform_id}'.encode()).hexdigest()
                wsSecret = hashlib.md5(
                    f'{ws_secret_prefix}_{convert_uid}_{streamname}_{ws_secret_hash}_{wsTime}'.encode()).hexdigest()
                qs['seqid'] = seqid
                qs['ver'] = '1'
                qs['u'] = convert_uid
                qs['t'] = platform_id
                qs['sv'] = '2401090219'
                qs['sdk_sid'] = str(int(time.time() * 1000))
                qs['codec'] = '264'
                qs['wsSecret'] = wsSecret
                qs['ratio'] = iBitRate
                del qs['fm']
                url = update_scheme("http://", f"{flvurl}/{streamname}.{suffix}")
                url = update_qsd(url, qs)

                name = f"{cdntype.lower()}_{iBitRate}"
                priority = 20000 if iBitRate == 0 else iBitRate
                self.QUALITY_WEIGHTS[name] = self._QUALITY_WEIGHTS_OVERRIDE.get(name, priority)
                yield name, HTTPStream(self.session, url)

        log.debug(f"QUALITY_WEIGHTS: {self.QUALITY_WEIGHTS!r}")


__plugin__ = Huya
