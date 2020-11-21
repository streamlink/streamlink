import logging
import re
from urllib.parse import parse_qsl, urlparse, urlunparse

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class Swisstxt(Plugin):
    url_re = re.compile(r"""https?://(?:
        live\.(rsi)\.ch/|
        (?:www\.)?(srf)\.ch/sport/resultcenter
    )""", re.VERBOSE)
    api_url = "http://event.api.swisstxt.ch/v1/stream/{site}/byEventItemIdAndType/{id}/HLS"

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None and cls.get_event_id(url)

    @classmethod
    def get_event_id(cls, url):
        return dict(parse_qsl(urlparse(url).query.lower())).get("eventid")

    def get_stream_url(self, event_id):
        url_m = self.url_re.match(self.url)
        site = url_m.group(1) or url_m.group(2)
        api_url = self.api_url.format(id=event_id, site=site.upper())
        log.debug("Calling API: {0}".format(api_url))

        stream_url = self.session.http.get(api_url).text.strip("\"'")

        parsed = urlparse(stream_url)
        query = dict(parse_qsl(parsed.query))
        return urlunparse(parsed._replace(query="")), query

    def _get_streams(self):
        stream_url, params = self.get_stream_url(self.get_event_id(self.url))
        return HLSStream.parse_variant_playlist(self.session,
                                                stream_url,
                                                params=params)


__plugin__ = Swisstxt
