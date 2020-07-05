import re
import logging

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HDSStream, HLSStream, HTTPStream
from streamlink.utils import update_scheme
from streamlink.exceptions import PluginError

MEDIA_URL = "http://www.ardmediathek.de/play/media/{0}"
SWF_URL = "http://www.ardmediathek.de/ard/static/player/base/flash/PluginFlash.swf"
HDCORE_PARAMETER = "?hdcore=3.3.0"
QUALITY_MAP = {
    "auto": "auto",
    4: "1080p",
    3: "720p",
    2: "544p",
    1: "360p",
    0: "144p"
}

_url_re = re.compile(r"https?://(?:(\w+\.)?ardmediathek\.de/|mediathek\.daserste\.de/)")
_media_id_re = re.compile(r"/play/(?:media|config|sola)/(\d+)")
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

log = logging.getLogger(__name__)


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
            stream = HTTPStream(self.session, update_scheme("https://", url))
            yield name, stream

    def _get_hds_streams(self, info):
        # Needs the hdcore parameter added
        url = info["_stream"] + HDCORE_PARAMETER
        return HDSStream.parse_manifest(self.session, update_scheme("https://", url), pvswf=SWF_URL).items()

    def _get_hls_streams(self, info):
        return HLSStream.parse_variant_playlist(self.session, update_scheme("https://", info["_stream"])).items()

    def _get_smil_streams(self, info):
        res = self.session.http.get(update_scheme("https://", info["_stream"]))
        smil = self.session.http.xml(res, "SMIL config", schema=_smil_schema)

        for video in smil["videos"]:
            url = "{0}/{1}{2}".format(smil["base"], video, HDCORE_PARAMETER)
            streams = HDSStream.parse_manifest(self.session, url, pvswf=SWF_URL, is_akamai=smil["cdn"] == "akamai")

            for stream in streams.items():
                yield stream

    def _get_streams(self):
        res = self.session.http.get(self.url)
        match = _media_id_re.search(res.text)
        if match:
            media_id = match.group(1)
        else:
            return

        log.debug("Found media id: {0}", media_id)

        res = self.session.http.get(MEDIA_URL.format(media_id))
        media = self.session.http.json(res, schema=_media_schema)

        for media in media["_mediaArray"]:
            for stream in media["_mediaStreamArray"]:
                stream_ = stream["_stream"]
                if isinstance(stream_, list):
                    if not stream_:
                        continue
                    stream_ = stream_[0]

                stream_ = update_scheme("https://", stream_)
                if stream_.endswith(".f4m"):
                    parser = self._get_hds_streams
                    parser_name = "HDS"
                elif stream_.endswith(".smil"):
                    parser = self._get_smil_streams
                    parser_name = "SMIL"
                elif ".m3u8" in stream_:
                    parser = self._get_hls_streams
                    parser_name = "HLS"
                elif stream_.startswith("http"):
                    parser = self._get_http_streams
                    parser_name = "HTTP"
                else:
                    raise PluginError("Unexpected stream type: '{0}'".format(stream_))

                try:
                    for s in parser(stream):
                        yield s
                except IOError as err:
                    log.debug("Failed to extract {0} streams: {1}".format(parser_name, err))


__plugin__ = ard_mediathek
