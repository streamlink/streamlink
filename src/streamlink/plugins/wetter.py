import logging
import re

from streamlink.exceptions import PluginError
from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream, HTTPStream, RTMPStream

log = logging.getLogger(__name__)


class Wetter(Plugin):
    _url_re = re.compile(r"https?://(?:www\.)?wetter\.com/")
    _videourl_re = re.compile(r'data-video-url-(hls|rtmp|endpoint)\s*=\s*"(.+)"')

    _stream_schema = validate.Schema(
        validate.transform(_videourl_re.findall),
        validate.transform(lambda vl: [{"stream-type": v[0], "url": v[1]} for v in vl]),
        [
            {
                "stream-type": validate.text,
                "url": validate.url(),
            }
        ],
    )
    _endpoint_schema = validate.Schema(
        [
            {
                validate.optional("label"): validate.text,
                "type": "video/mp4",
                "file": validate.url(scheme="http"),
            }
        ],
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        try:
            streams = self.session.http.get(self.url, schema=self._stream_schema)
        except PluginError as err:
            log.debug(err)
            return

        for stream in streams:
            if stream["stream-type"] == "hls":
                for s in HLSStream.parse_variant_playlist(self.session, stream["url"]).items():
                    yield s
            elif stream["stream-type"] == "rtmp":
                yield "0live", RTMPStream(self.session, {"rtmp": stream["url"]})
            elif stream["stream-type"] == "endpoint":
                res = self.session.http.get(stream["url"])
                files = self.session.http.json(res, schema=self._endpoint_schema)
                for f in files:
                    s = HTTPStream(self.session, f["file"])
                    yield "vod", s


__plugin__ = Wetter
