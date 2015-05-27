import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import HLSStream

_url_re = re.compile("http://(?:www\.)?tvcatchup.com/watch/\w+")
_stream_re = re.compile(r"\"(?P<stream_url>http://.*m3u8.*clientKey=[^\"]*)\";")


class TVCatchup(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        """
        Finds the stream from tvcatchup, they only provide a single 720p stream per channel.
        """
        res = http.get(self.url)

        match = _stream_re.search(res.text, re.IGNORECASE | re.MULTILINE)

        if match:
            stream_url = match.groupdict()["stream_url"]

            if stream_url:
                if "_adp" in stream_url:
                    return HLSStream.parse_variant_playlist(self.session, stream_url)
                else:
                    return {'576p': HLSStream(self.session, stream_url)}


__plugin__ = TVCatchup
