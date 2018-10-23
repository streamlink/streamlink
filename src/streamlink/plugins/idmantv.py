import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink import NoStreamsError


class IdmanTV(Plugin):

    _url_re = re.compile(r"https?://player\.tvibo\.com/aztv/(?P<id>\d+)")
    _api_url = "http://panel.tvibo.com/api/player/streamurl/{id}"

    _api_response_schema = validate.Schema({
        u"st": validate.url()
    }, validate.get("st"))

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        channel_id = self._url_re.match(self.url).group("id")

        try:
            api_response = self.session.http.get(
                           self._api_url.format(id=channel_id))

            stream_url = self.session.http.json(
                         api_response,
                         schema=self._api_response_schema)
        except Exception:
            raise NoStreamsError(self.url)

        print(stream_url)

        yield "source", HLSStream(self.session, stream_url)


__plugin__ = IdmanTV
