import re
import logging

from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class CLLive(Plugin):
    _url_re = re.compile(r"https?://(?:www\.)?cl-live\.com/.+/ondemand/([^/]+)$")
    _key_re = re.compile(
        r"""\"key\":\"([\w\d]+)\",""",
        re.M)
    _token_re = re.compile(
        r"""\\u002F([\d]+)\\u002Fhls.m3u8""",
        re.M)
    _cookie_url = "https://api.cl-live.com/v1/license/ondemand/{0}"
    _hls_url = "https://ondemand.cl-live.com/{0}/ondemand/{1}/hls.m3u8"

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        page = self.session.http.get(
            self.url,
            allow_redirects=True,
            headers={"User-Agent": useragents.IPHONE_6}
        )

        key = self._key_re.search(page.text)
        token = self._token_re.search(page.text)
        log.debug("X-API-KEY: {0}".format(key.group(1)))
        log.debug("Token: {0}".format(token.group(1)))

        vid = self._url_re.match(self.url)

        _ = self.session.http.get(
            self._cookie_url.format(vid.group(1)),
            allow_redirects=True,
            headers={
                "User-Agent": useragents.IPHONE_6,
                "X-API-Key": key.group(1)
            }
        )

        playlisturl = self._hls_url.format(vid.group(1), token.group(1))
        log.debug("Video Url: {0}".format(playlisturl))

        streams = HLSStream.parse_variant_playlist(self.session, playlisturl)
        log.debug(streams)

        if not streams:
            return {"live": HLSStream(self.session, playlisturl)}
        else:
            return streams


__plugin__ = CLLive
