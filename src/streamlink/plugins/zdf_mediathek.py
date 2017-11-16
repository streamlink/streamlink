import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HDSStream, HLSStream
from streamlink.utils import parse_json

API_URL = "https://api.zdf.de"

QUALITY_WEIGHTS = {
    "hd": 720,
    "veryhigh": 480,
    "high": 240,
    "med": 176,
    "low": 112
}

STREAMING_TYPES = {
    "h264_aac_f4f_http_f4m_http": (
        "HDS", HDSStream.parse_manifest
    ),
    "h264_aac_ts_http_m3u8_http": (
        "HLS", HLSStream.parse_variant_playlist
    )
}

_url_re = re.compile(r"""
    http(s)?://(\w+\.)?zdf.de/
""", re.VERBOSE | re.IGNORECASE)
_api_json_re = re.compile(r'''data-zdfplayer-jsb=["'](?P<json>{.+?})["']''', re.S)

_api_schema = validate.Schema(
    validate.transform(_api_json_re.search),
    validate.any(
        None,
        validate.all(
            validate.get("json"),
            validate.transform(parse_json),
            {
                "content": validate.text,
                "apiToken": validate.text
            },
        )
    )
)

_documents_schema = validate.Schema(
    {
        "mainVideoContent": {
            "http://zdf.de/rels/target": {
                "http://zdf.de/rels/streams/ptmd": validate.text
            },
        },
    }
)

_schema = validate.Schema(
    {
        "priorityList": [
            {
                "formitaeten": [
                    {
                        "type": validate.text,
                        "qualities": [
                            {
                                "audio": {
                                    "tracks": [
                                        {
                                            "uri": validate.text
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ]
            }
        ]
    }
)


class zdf_mediathek(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    @classmethod
    def stream_weight(cls, key):
        weight = QUALITY_WEIGHTS.get(key)
        if weight:
            return weight, "zdf_mediathek"

        return Plugin.stream_weight(key)

    def _extract_streams(self, response):
        if "priorityList" not in response:
            self.logger.error("Invalid response! Contains no priorityList!")

        for priority in response["priorityList"]:
            for format_ in priority["formitaeten"]:
                yield self._extract_from_format(format_)

    def _parse_track(self, track, parser, name):
        try:
            return parser(self.session, track["uri"])
        except IOError as err:
            self.logger.error("Failed to extract {0} streams: {1}", name, err)

    def _extract_from_format(self, format_):
        qualities = {}

        if format_["type"] not in STREAMING_TYPES:
            return qualities

        name, parser = STREAMING_TYPES[format_["type"]]
        for quality in format_["qualities"]:
            for track in quality["audio"]["tracks"]:
                option = self._parse_track(track, parser, name)
                if option:
                    qualities.update(option)

        return qualities

    def _get_streams(self):
        zdf_json = http.get(self.url, schema=_api_schema)
        if zdf_json is None:
            return

        headers = {
            "Api-Auth": "Bearer {0}".format(zdf_json['apiToken']),
            "Referer": self.url
        }

        res = http.get(zdf_json['content'], headers=headers)
        document = http.json(res, schema=_documents_schema)

        stream_request_url = document["mainVideoContent"]["http://zdf.de/rels/target"]["http://zdf.de/rels/streams/ptmd"]
        stream_request_url = API_URL + stream_request_url

        res = http.get(stream_request_url, headers=headers)
        res = http.json(res, schema=_schema)

        streams = {}
        for format_ in self._extract_streams(res):
            streams.update(format_)

        return streams


__plugin__ = zdf_mediathek
