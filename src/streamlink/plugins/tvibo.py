import logging
import re

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class Tvibo(Plugin):

    _url_re = re.compile(r"https?://player\.tvibo\.com/\w+/(?P<id>\d+)")
    _api_url = "http://panel.tvibo.com/api/player/streamurl/{id}"

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        channel_id = self._url_re.match(self.url).group("id")

        api_response = self.session.http.get(
            self._api_url.format(id=channel_id),
            acceptable_status=(200, 404))

        data = self.session.http.json(api_response)
        log.trace("{0!r}".format(data))
        if data.get("st"):
            yield "source", HLSStream(self.session, data["st"])
        elif data.get("error"):
            log.error(data["error"]["message"])


__plugin__ = Tvibo
