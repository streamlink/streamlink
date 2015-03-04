import re

from livestreamer import PluginError
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import HLSStream

SUCCESS_HTTP_CODES = (200,)

STREAM_URL_FORMAT = "http://tvcatchup.com/stream.php?chan={0}"
_url_re = re.compile("http://(?:www\.)?tvcatchup.com/watch/(?P<channel_id>[0-9]+)")


class TVCatchup(Plugin):
    def __init__(self, url):
        Plugin.__init__(self, url)
        match = _url_re.match(url).groupdict()
        self.channel_id = match["channel_id"]

    @classmethod
    def can_handle_url(self, url):
        print "hi!", url
        return _url_re.match(url)

    def _get_streams(self):
        res = http.get(STREAM_URL_FORMAT.format(self.channel_id))

        stream_url = res.status_code in SUCCESS_HTTP_CODES and res.json().get('url')

        if not stream_url:
            raise PluginError("The program is not available, please try again later")

        return {"480p": HLSStream(self.session, stream_url)}


__plugin__ = TVCatchup
