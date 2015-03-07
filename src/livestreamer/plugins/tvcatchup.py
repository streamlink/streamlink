import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import HLSStream

SUCCESS_HTTP_CODES = (200,)

STREAM_URL_FORMAT = "http://tvcatchup.com/stream.php?chan={0}"
_url_re = re.compile("http://(?:www\.)?tvcatchup.com/watch/(?P<channel_id>[0-9]+)")


class TVCatchup(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        """
        Finds the stream from tvcatchup, they only provide a single 480p stream per channel.
        """
        match = _url_re.match(self.url).groupdict()
        channel_id = match["channel_id"]

        res = http.get(STREAM_URL_FORMAT.format(channel_id))

        stream_url = http.json(res).get('url')

        if stream_url:
            return {"480p": HLSStream(self.session, stream_url)}


__plugin__ = TVCatchup
