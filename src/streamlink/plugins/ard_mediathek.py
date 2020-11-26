import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream, HTTPStream
from streamlink.utils import update_scheme

MEDIA_URL = "http://www.ardmediathek.de/play/media/{0}"
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

log = logging.getLogger(__name__)


class ard_mediathek(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url) is not None

    def _get_http_streams(self, info):
        name = QUALITY_MAP.get(info["_quality"], "vod")
        urls = info["_stream"]
        if not isinstance(info["_stream"], list):
            urls = [urls]

        for url in urls:
            stream = HTTPStream(self.session, update_scheme("https://", url))
            yield name, stream

    def _get_hls_streams(self, info):
        return HLSStream.parse_variant_playlist(self.session, update_scheme("https://", info["_stream"])).items()

    def _get_streams(self):
        res = self.session.http.get(self.url)
        match = _media_id_re.search(res.text)
        if match:
            media_id = match.group(1)
        else:
            return

        log.debug("Found media id: {0}".format(media_id))
        res = self.session.http.get(MEDIA_URL.format(media_id))
        media = self.session.http.json(res, schema=_media_schema)
        log.trace("{0!r}".format(media))

        for media in media["_mediaArray"]:
            for stream in media["_mediaStreamArray"]:
                stream_ = stream["_stream"]
                if isinstance(stream_, list):
                    if not stream_:
                        continue
                    stream_ = stream_[0]

                stream_ = update_scheme("https://", stream_)
                if ".m3u8" in stream_:
                    parser = self._get_hls_streams
                    parser_name = "HLS"
                elif (".mp4" in stream_ and ".f4m" not in stream_):
                    parser = self._get_http_streams
                    parser_name = "HTTP"
                else:
                    log.error("Unexpected stream type: '{0}'".format(stream_))

                try:
                    yield from parser(stream)
                except OSError as err:
                    log.error("Failed to extract {0} streams: {1}".format(parser_name, err))


__plugin__ = ard_mediathek
