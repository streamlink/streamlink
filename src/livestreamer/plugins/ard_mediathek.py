import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import HTTPStream, HDSStream, RTMPStream

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

_url_re = re.compile("http(s)?://(\w+\.)?ardmediathek.de/tv")
_media_id_re = re.compile("/play/config/(\d+)")
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

    def _get_rtmp_streams(self, info):
        name = QUALITY_MAP.get(info["_quality"], "live")
        params = {
            "rtmp": info["_server"].strip(),
            "playpath": info["_stream"],
            "pageUrl": self.url,
            "swfVfy": SWF_URL,
            "live": True
        }
        stream = RTMPStream(self.session, params)
        yield name, stream

    def _get_smil_streams(self, info):
        res = http.get(info["_stream"])
        smil = http.xml(res, "SMIL config", schema=_smil_schema)

        for video in smil["videos"]:
            url = "{0}/{1}{2}".format(smil["base"], video, HDCORE_PARAMETER)
            streams = HDSStream.parse_manifest(self.session, url, pvswf=SWF_URL)

            # TODO: Replace with "yield from" when dropping Python 2.
            for stream in streams.items():
                yield stream

    def _get_streams(self):
        res = http.get(self.url)
        match = _media_id_re.search(res.text)
        if match:
            media_id = match.group(1)
        else:
            return

        res = http.get(MEDIA_URL.format(media_id))
        media = http.json(res, schema=_media_schema)

        for media in media["_mediaArray"]:
            for stream in media["_mediaStreamArray"]:
                server = stream.get("_server", "").strip()
                stream_ = stream["_stream"]
                if isinstance(stream_, list):
                    if not stream_:
                        continue
                    stream_ = stream_[0]
                stream_ = stream_.strip()

                if server.startswith("rtmp://"):
                    parser = self._get_rtmp_streams
                    parser_name = "RTMP"
                elif stream_.endswith(".f4m"):
                    parser = self._get_hds_streams
                    parser_name = "HDS"
                elif stream_.endswith(".smil"):
                    parser = self._get_smil_streams
                    parser_name = "SMIL"
                elif stream_.startswith("http"):
                    parser = self._get_http_streams
                    parser_name = "HTTP"

                try:
                    # TODO: Replace with "yield from" when dropping Python 2.
                    for stream in parser(stream):
                        yield stream
                except IOError as err:
                    self.logger.error("Failed to extract {0} streams: {1}",
                                      parser_name, err)

__plugin__ = ard_mediathek
