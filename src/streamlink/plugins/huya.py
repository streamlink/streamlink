import base64
import logging
import re
from html import unescape as html_unescape

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HTTPStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)


class Huya(Plugin):
    _re_url = re.compile(r'https?://(?:www\.)?huya\.com/(?P<channel>[^/]+)')
    _re_stream = re.compile(r'"stream"\s?:\s?"([^"]+)"')
    _schema_data = validate.Schema(
        {
            # 'status': int,
            # 'msg': validate.any(None, str),
            'data': [{
                'gameStreamInfoList': [{
                    'sCdnType': str,
                    'sStreamName': str,
                    'sFlvUrl': str,
                    'sFlvUrlSuffix': str,
                    'sFlvAntiCode': validate.all(str, validate.transform(lambda v: html_unescape(v))),
                    # 'sHlsUrl': str,
                    # 'sHlsUrlSuffix': str,
                    # 'sHlsAntiCode': validate.all(str, validate.transform(lambda v: html_unescape(v))),
                    validate.optional('iIsMultiStream'): int,
                    'iPCPriorityRate': int,
                }]
            }],
            # 'vMultiStreamInfo': [{
            #    'sDisplayName': str,
            #    'iBitRate': int,
            # }],
        },
        validate.get('data'),
        validate.get(0),
        validate.get('gameStreamInfoList'),
    )
    QUALITY_WEIGHTS = {}

    @classmethod
    def can_handle_url(cls, url):
        return cls._re_url.match(url) is not None

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
            log.trace(f'{info!r}')
            flv_url = f'{info["sFlvUrl"]}/{info["sStreamName"]}.{info["sFlvUrlSuffix"]}?{info["sFlvAntiCode"]}'
            name = f'source_{info["sCdnType"].lower()}'
            self.QUALITY_WEIGHTS[name] = info['iPCPriorityRate']
            yield name, HTTPStream(self.session, flv_url)

        log.debug(f'QUALITY_WEIGHTS: {self.QUALITY_WEIGHTS!r}')


__plugin__ = Huya
