"""
Plugin for vidio.com
- https://www.vidio.com/live/5075-dw-tv-stream
- https://www.vidio.com/watch/766861-5-rekor-fantastis-zidane-bersama-real-madrid
"""
import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents, validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)


class Vidio(Plugin):
    _url_re = re.compile(r"https?://(?:www\.)?vidio\.com/(?:en/)?(?P<type>live|watch)/(?P<id>\d+)-(?P<name>[^/?#&]+)")
    _playlist_re = re.compile(r'''hls-url=["'](?P<url>[^"']+)["']''')
    _data_id_re = re.compile(r'''meta\s+data-id=["'](?P<id>[^"']+)["']''')

    csrf_tokens_url = "https://www.vidio.com/csrf_tokens"
    tokens_url = "https://www.vidio.com/live/{id}/tokens"
    token_schema = validate.Schema(validate.transform(parse_json),
                                   {"token": validate.text},
                                   validate.get("token"))

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    def get_csrf_tokens(self):
        return self.session.http.get(
            self.csrf_tokens_url,
            schema=self.token_schema
        )

    def get_url_tokens(self, stream_id):
        log.debug("Getting stream tokens")
        csrf_token = self.get_csrf_tokens()
        return self.session.http.post(
            self.tokens_url.format(id=stream_id),
            files={"authenticity_token": (None, csrf_token)},
            headers={
                "User-Agent": useragents.CHROME,
                "Referer": self.url
            },
            schema=self.token_schema
        )

    def _get_streams(self):
        res = self.session.http.get(self.url)

        plmatch = self._playlist_re.search(res.text)
        idmatch = self._data_id_re.search(res.text)

        hls_url = plmatch and plmatch.group("url")
        stream_id = idmatch and idmatch.group("id")

        tokens = self.get_url_tokens(stream_id)

        if hls_url:
            log.debug("HLS URL: {0}".format(hls_url))
            log.debug("Tokens: {0}".format(tokens))
            return HLSStream.parse_variant_playlist(self.session,
                                                    hls_url + "?" + tokens,
                                                    headers={"User-Agent": useragents.CHROME,
                                                             "Referer": self.url})


__plugin__ = Vidio
