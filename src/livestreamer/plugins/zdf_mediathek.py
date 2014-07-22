import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import HDSStream, HLSStream, RTMPStream

API_URL = "http://www.zdf.de/ZDFmediathek/xmlservice/web/beitragsDetails"
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
    http(s)?://(\w+\.)?zdf.de/zdfmediathek(\#)?/.+
    /(live|video)
    /(?P<video_id>\d+)
""", re.VERBOSE | re.IGNORECASE)

_schema = validate.Schema(
    validate.xml_findall("video/formitaeten/formitaet"),
    [
        validate.union({
            "type": validate.get("basetype"),
            "quality": validate.xml_findtext("quality"),
            "url": validate.all(
                validate.xml_findtext("url"),
                validate.url()
            )
        })
    ]
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

    def _create_rtmp_stream(self, url):
        return RTMPStream(self.session, {
            "rtmp": self._get_meta_url(url),
            "pageUrl": self.url,
        })

    def _get_meta_url(self, url):
        res = http.get(url, exception=IOError)
        root = http.xml(res, exception=IOError)
        return root.findtext("default-stream-url")

    def _get_streams(self):
        match = _url_re.match(self.url)
        video_id = match.group("video_id")
        res = http.get(API_URL, params=dict(ak="web", id=video_id))
        fmts = http.xml(res, schema=_schema)

        streams = {}
        for fmt in fmts:
            if fmt["type"] in STREAMING_TYPES:
                name, parser = STREAMING_TYPES[fmt["type"]]
                try:
                    streams.update(parser(self.session, fmt["url"]))
                except IOError as err:
                    self.logger.error("Failed to extract {0} streams: {1}",
                                      name, err)

            elif fmt["type"] == "h264_aac_mp4_rtmp_zdfmeta_http":
                name = fmt["quality"]
                try:
                    streams[name] = self._create_rtmp_stream(fmt["url"])
                except IOError as err:
                    self.logger.error("Failed to extract RTMP stream '{0}': {1}",
                                      name, err)

        return streams

__plugin__ = zdf_mediathek
