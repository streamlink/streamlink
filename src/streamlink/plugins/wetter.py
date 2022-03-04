"""
$url wetter.com
$type live, vod
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream, HTTPStream, RTMPStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?wetter\.com/"
))
class Wetter(Plugin):
    _videourl_re = re.compile(r'data-video-url-(hls|rtmp|endpoint|mp4)\s*=\s*"(.+)"')

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

    def _get_streams(self):
        streams = self.session.http.get(self.url, schema=self._stream_schema)
        for stream in streams:
            if stream["stream-type"] == "hls":
                streams = HLSStream.parse_variant_playlist(self.session, stream["url"]).items()
                if streams:
                    for s in streams:
                        yield s
                else:
                    yield "live", HLSStream(self.session, stream["url"])
            elif stream["stream-type"] == "rtmp":
                yield "0_live", RTMPStream(self.session, {"rtmp": stream["url"]})
            elif stream["stream-type"] == "endpoint":
                res = self.session.http.get(stream["url"])
                files = self.session.http.json(res, schema=self._endpoint_schema)
                for f in files:
                    s = HTTPStream(self.session, f["file"])
                    yield "vod", s
            elif stream["stream-type"] == "mp4":
                yield "vod", HTTPStream(self.session, stream["url"])


__plugin__ = Wetter
