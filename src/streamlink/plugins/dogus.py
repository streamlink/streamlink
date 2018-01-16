import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.stream import HLSStream
from streamlink.utils import update_scheme


class Dogus(Plugin):
    """
    Support for live streams from Dogus sites include ntv, ntvspor, and kralmuzik
    """

    url_re = re.compile(r"""https?://(?:www.)?
        (?:
            ntv.com.tr/canli-yayin/ntv|
            ntvspor.net/canli-yayin|
            kralmuzik.com.tr/tv/kral-tv|
            kralmuzik.com.tr/tv/kral-pop-tv|
            eurostartv.com.tr/canli-izle
        )/?""", re.VERBOSE)
    mobile_url_re = re.compile(r"""(?P<q>["'])(?P<url>(https?:)?//[^'"]*?/live/hls/[^'"]*?\?token=)
                                   (?P<token>[^'"]*?)(?P=q)""", re.VERBOSE)
    token_re = re.compile(r"""token=(?P<q>["'])(?P<token>[^'"]*?)(?P=q)""")

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = http.get(self.url)
        mobile_url_m = self.mobile_url_re.search(res.text)

        mobile_url = mobile_url_m and update_scheme(self.url, mobile_url_m.group("url"))

        token = mobile_url_m and mobile_url_m.group("token")
        if not token:
            # if no token is in the url, try to find it else where in the page
            token_m = self.token_re.search(res.text)
            token = token_m and token_m.group("token")

        return HLSStream.parse_variant_playlist(self.session, mobile_url + token,
                                                headers={"Referer": self.url})


__plugin__ = Dogus
