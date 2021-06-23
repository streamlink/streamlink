import logging
import re
from urllib.parse import urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api.utils import itertags
from streamlink.stream import HLSStream
from streamlink.utils import update_scheme

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?
    (?:
        eurostartv\.com\.tr/canli-izle|
        kralmuzik\.com\.tr/tv/|
        ntv\.com\.tr/canli-yayin/ntv|
        startv\.com\.tr/canli-yayin
    )/?
""", re.VERBOSE))
class Dogus(Plugin):
    mobile_url_re = re.compile(r"""(?P<q>["'])(?P<url>(https?:)?//[^'"]*?/live/hls/[^'"]*?\?token=)
                                   (?P<token>[^'"]*?)(?P=q)""", re.VERBOSE)
    token_re = re.compile(r"""token=(?P<q>["'])(?P<token>[^'"]*?)(?P=q)""")
    kral_token_url = "https://service.kralmuzik.com.tr/version/gettoken"

    def _get_streams(self):
        res = self.session.http.get(self.url)

        # Look for Youtube embedded video first
        for iframe in itertags(res.text, "iframe"):
            if urlparse(iframe.attributes.get("src")).netloc.endswith("youtube.com"):
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
