import re

from livestreamer.compat import urlparse
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import StreamMapper, http, validate
from livestreamer.stream import HLSStream, RTMPStream

CHANNEL_URL = "http://www.mobileonline.tv/channel.php"

_url_re = re.compile("http(s)?://(\w+\.)?(ilive.to|streamlive.to)/.*/(?P<channel>\d+)")
_link_re = re.compile("<a href=(\S+) target=\"_blank\"")
_schema = validate.Schema(
    validate.transform(_link_re.findall),
)


class StreamLive(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _create_hls_streams(self, url):
        try:
            streams = HLSStream.parse_variant_playlist(self.session, url)
            return streams.items()
        except IOError as err:
            self.logger.warning("Failed to extract HLS streams: {0}", err)

    def _create_rtmp_stream(self, url):
        parsed = urlparse(url)
        if parsed.query:
            app = "{0}?{1}".format(parsed.path[1:], parsed.query)
        else:
            app = parsed.path[1:]

        params = {
            "rtmp": url,
            "app": app,
            "pageUrl": self.url,
            "live": True
        }

        stream = RTMPStream(self.session, params)
        return "live", stream

    def _get_streams(self):
        channel = _url_re.match(self.url).group("channel")
        urls = http.get(CHANNEL_URL, params=dict(n=channel), schema=_schema)
        if not urls:
            return

        mapper = StreamMapper(cmp=lambda scheme, url: url.startswith(scheme))
        mapper.map("http", self._create_hls_streams)
        mapper.map("rtmp", self._create_rtmp_stream)

        return mapper(urls)

__plugin__ = StreamLive
