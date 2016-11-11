import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HDSStream, HLSStream
from streamlink.plugin.api.utils import parse_query

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

_url_re = re.compile("""
    http(s)?://(\w+\.)?zdf.de/
""", re.VERBOSE | re.IGNORECASE)

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

    def _get_streams(self):
        match = _url_re.match(self.url)
        title = self.url.rsplit('/', 1)[-1]
        if title.endswith(".html"):
            title = title[:-5]

        request_url = "https://api.zdf.de/content/documents/%s.json?profile=player" % title
        res = http.get(request_url, headers={"Api-Auth" : "Bearer d2726b6c8c655e42b68b0db26131b15b22bd1a32"})
        document = http.json(res, schema=_documents_schema)

        stream_request_url = document["mainVideoContent"]["http://zdf.de/rels/target"]["http://zdf.de/rels/streams/ptmd"]
        stream_request_url = API_URL + stream_request_url

        res = http.get(stream_request_url)
        res = http.json(res, schema=_schema)
        formatList = res["priorityList"]["formitaeten"]

        streams = {}
        for format_ in formatList:
            if format_["type"] in STREAMING_TYPES:
                name, parser = STREAMING_TYPES[format_["type"]]
                for quality in format_["qualities"]:
                    tracks = quality["audio"]["tracks"]
                    for track in tracks:
                        try:
                            streams.update(parser(self.session, track["uri"]))
                        except IOError as err:
                            self.logger.error("Failed to extract {0} streams: {1}",
                                            name, err)

        return streams

__plugin__ = zdf_mediathek
