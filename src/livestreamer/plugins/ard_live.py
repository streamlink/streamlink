import re

from functools import partial

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import HLSStream, HDSStream


STREAM_INFO_URL = "http://live.daserste.de/{0}/livestream.xml"
SWF_URL = "http://live.daserste.de/lib/br-player/swf/main.swf"
STREAMING_TYPES = {
    "streamingUrlLive": (
        "HDS", partial(HDSStream.parse_manifest, pvswf=SWF_URL)
    ),
    "streamingUrlIPhone": (
        "HLS", HLSStream.parse_variant_playlist
    )
}

_url_re = re.compile("http(s)?://live.daserste.de/(?P<channel>[^/?]+)?")

_livestream_schema = validate.Schema(
    validate.xml_findall("video/*"),
    validate.filter(lambda e: e.tag in STREAMING_TYPES),
    validate.map(lambda e: (STREAMING_TYPES.get(e.tag), e.text)),
    validate.transform(dict),
)

class ard_live(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        channel = match.group("channel")
        res = http.get(STREAM_INFO_URL.format(channel))
        urls = http.xml(res, schema=_livestream_schema)

        streams = {}
        for (name, parser), url in urls.items():
            try:
                streams.update(parser(self.session, url))
            except IOError as err:
                self.logger.warning("Unable to extract {0} streams: {1}", name, err)

        return streams

__plugin__ = ard_live
