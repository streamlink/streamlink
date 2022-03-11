"""
$description Chinese live streaming platform for live video game broadcasts and individual live streams.
$url huya.com
$type live
"""

import base64
import logging
import re

from streamlink.compat import html_unescape
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.http import HTTPStream
from streamlink.utils.parse import parse_json

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r'https?://(?:www\.)?huya\.com/(?P<channel>[^/]+)'
))
class Huya(Plugin):
    _re_stream = re.compile(r'"stream"\s?:\s?"([^"]+)"')
    _schema_data = validate.Schema(
        {
            # 'status': int,
            # 'msg': validate.any(None, validate.text),
            'data': [{
                'gameStreamInfoList': [{
                    'sCdnType': validate.text,
                    'sStreamName': validate.text,
                    'sFlvUrl': validate.text,
                    'sFlvUrlSuffix': validate.text,
                    'sFlvAntiCode': validate.all(validate.text, validate.transform(lambda v: html_unescape(v))),
                    # 'sHlsUrl': validate.text,
                    # 'sHlsUrlSuffix': validate.text,
                    # 'sHlsAntiCode': validate.all(validate.text, validate.transform(lambda v: html_unescape(v))),
                    validate.optional('iIsMultiStream'): int,
                    'iPCPriorityRate': int,
                }]
            }],
            # 'vMultiStreamInfo': [{
            #    'sDisplayName': validate.text,
            #    'iBitRate': int,
            # }],
        },
        validate.get('data'),
        validate.get(0),
        validate.get('gameStreamInfoList'),
    )
    QUALITY_WEIGHTS = {}

    @classmethod
    def stream_weight(cls, key):
        weight = cls.QUALITY_WEIGHTS.get(key)
        if weight:
            return weight, 'huya'

        return Plugin.stream_weight(key)

    def _get_streams(self):
        res = self.session.http.get(self.url)
        data = self._re_stream.search(res.text)

        if not data:
            return

        data = parse_json(base64.b64decode(data.group(1)), schema=self._schema_data)
        for info in data:
            log.trace('{0!r}'.format(info))
            flv_url = '{0}/{1}.{2}?{3}'.format(info["sFlvUrl"], info["sStreamName"], info["sFlvUrlSuffix"],
                                               info["sFlvAntiCode"])
            name = 'source_{0}'.format(info["sCdnType"].lower())
            self.QUALITY_WEIGHTS[name] = info['iPCPriorityRate']
            yield name, HTTPStream(self.session, flv_url)

        log.debug('QUALITY_WEIGHTS: {0!r}'.format(self.QUALITY_WEIGHTS))


__plugin__ = Huya
