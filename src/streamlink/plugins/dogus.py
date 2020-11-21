import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api.utils import itertags
from streamlink.plugins.youtube import YouTube
from streamlink.stream import HLSStream
from streamlink.utils import update_scheme

log = logging.getLogger(__name__)


class Dogus(Plugin):
    """
    Support for live streams from Dogus sites include ntv, ntvspor, and kralmuzik
    """

    url_re = re.compile(r"""https?://(?:www.)?
        (?:
            ntv.com.tr/canli-yayin/ntv|
            ntvspor.net/canli-yayin|
            kralmuzik.com.tr/tv/|
            eurostartv.com.tr/canli-izle|
            startv.com.tr/canli-yayin
        )/?""", re.VERBOSE)
    mobile_url_re = re.compile(r"""(?P<q>["'])(?P<url>(https?:)?//[^'"]*?/live/hls/[^'"]*?\?token=)
                                   (?P<token>[^'"]*?)(?P=q)""", re.VERBOSE)
    token_re = re.compile(r"""token=(?P<q>["'])(?P<token>[^'"]*?)(?P=q)""")
    kral_token_url = "https://service.kralmuzik.com.tr/version/gettoken"

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = self.session.http.get(self.url)

        # Look for Youtube embedded video first
        for iframe in itertags(res.text, 'iframe'):
            if YouTube.can_handle_url(iframe.attributes.get("src")):
                log.debug("Handing off to YouTube plugin")
                return self.session.streams(iframe.attributes.get("src"))

        # Next check for HLS URL with token
        mobile_url_m = self.mobile_url_re.search(res.text)
        mobile_url = mobile_url_m and update_scheme(self.url, mobile_url_m.group("url"))
        if mobile_url:
            log.debug("Found mobile stream: {0}".format(mobile_url_m.group(0)))

            token = mobile_url_m and mobile_url_m.group("token")
            if not token and "kralmuzik" in self.url:
                log.debug("Getting Kral Muzik HLS stream token from API")
                token = self.session.http.get(self.kral_token_url).text
            elif not token:
                # if no token is in the url, try to find it else where in the page
                log.debug("Searching for HLS stream token in URL")
                token_m = self.token_re.search(res.text)
                token = token_m and token_m.group("token")

            return HLSStream.parse_variant_playlist(self.session, mobile_url + token,
                                                    headers={"Referer": self.url})


__plugin__ = Dogus
