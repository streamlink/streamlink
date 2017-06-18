import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HDSStream, HLSStream, HTTPStream

MEDIA_URL = "http://www.ardmediathek.de/play/media/{0}"
SWF_URL = "http://www.ardmediathek.de/ard/static/player/base/flash/PluginFlash.swf"
HDCORE_PARAMETER = "?hdcore=3.3.0"
QUALITY_MAP = {
    "auto": "auto",
    3: "544p",
    2: "360p",
    1: "288p",
    0: "144p"
}

_url_re = re.compile(r"http(s)?://(?:(\w+\.)?ardmediathek.de/tv|mediathek.daserste.de/)")
_media_id_re = re.compile(r"/play/(?:media|config)/(\d+)")
_media_schema = validate.Schema({
    "_mediaArray": [{
        "_mediaStreamArray": [{
            validate.optional("_server"): validate.text,
            "_stream": validate.any(validate.text, [validate.text]),
            "_quality": validate.any(int, validate.text)
        }]
    }]
})
_smil_schema = validate.Schema(
    validate.union({
        "base": validate.all(
            validate.xml_find("head/meta"),
            validate.get("base"),
            validate.url(scheme="http")
        ),
        "cdn": validate.all(
            validate.xml_find("head/meta"),
            validate.get("cdn")
        ),
        "videos": validate.all(
            validate.xml_findall("body/seq/video"),
            [validate.get("src")]
        )
    })
)


class ard_mediathek(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_http_streams(self, info):
        name = QUALITY_MAP.get(info["_quality"], "vod")
        urls = info["_stream"]
        if not isinstance(info["_stream"], list):
            urls = [urls]

        for url in urls:
            stream = HTTPStream(self.session, url)
            yield name, stream

    def _get_hds_streams(self, info):
        # Needs the hdcore parameter added
        url = info["_stream"] + HDCORE_PARAMETER
        return HDSStream.parse_manifest(self.session, url, pvswf=SWF_URL).items()

    def _get_hls_streams(self, info):
        return HLSStream.parse_variant_playlist(self.session, info["_stream"]).items()

    def _get_smil_streams(self, info):
        res = http.get(info["_stream"])
        smil = http.xml(res, "SMIL config", schema=_smil_schema)

        for video in smil["videos"]:
            url = "{0}/{1}{2}".format(smil["base"], video, HDCORE_PARAMETER)
            streams = HDSStream.parse_manifest(self.session, url, pvswf=SWF_URL, is_akamai=smil["cdn"] == "akamai")

            for stream in streams.items():
                yield stream

    def _get_streams(self):
        res = http.get(self.url)
        match = _media_id_re.search(res.text)
        if match:
            media_id = match.group(1)
        else:
            return

        self.logger.debug("Found media id: {0}", media_id)

        res = http.get(MEDIA_URL.format(media_id))
        media = http.json(res, schema=_media_schema)

        for media in media["_mediaArray"]:
            for stream in media["_mediaStreamArray"]:
                stream_ = stream["_stream"]
                if isinstance(stream_, list):
                    if not stream_:
                        continue
                    stream_ = stream_[0]

                if stream_.endswith(".f4m"):
                    parser = self._get_hds_streams
                    parser_name = "HDS"
                elif stream_.endswith(".smil"):
                    parser = self._get_smil_streams
                    parser_name = "SMIL"
                elif stream_.endswith(".m3u8"):
                    parser = self._get_hls_streams
                    parser_name = "HLS"
                elif stream_.startswith("http"):
                    parser = self._get_http_streams
                    parser_name = "HTTP"

                try:
                    for s in parser(stream):
                        yield s
                except IOError as err:
                    self.logger.error("Failed to extract {0} streams: {1}",
                                      parser_name, err)


__plugin__ = ard_mediathek
