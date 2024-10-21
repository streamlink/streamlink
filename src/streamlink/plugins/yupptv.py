"""
$description Indian live TV channels and video on-demand service. OTT service from YuppTV.
$url yupptv.com
$type live, vod
$account Some streams require an account and subscription
"""

import logging
import re
import time

from streamlink.plugin import Plugin, pluginargument, pluginmatcher
from streamlink.plugin.api import useragents
from streamlink.stream.hls import HLSStream, HLSStreamReader, HLSStreamWriter


log = logging.getLogger(__name__)


class HLSStreamWriterYupptv(HLSStreamWriter):
    def should_filter_segment(self, segment):
        return ".ts" not in segment.uri or super().should_filter_segment(segment)


class HLSStreamReaderYupptv(HLSStreamReader):
    __writer__ = HLSStreamWriterYupptv


class HLSStreamYupptv(HLSStream):
    __reader__ = HLSStreamReaderYupptv


@pluginmatcher(
    re.compile(r"https?://(?:www\.)?yupptv\.com"),
)
@pluginargument(
    "boxid",
    requires=["yuppflixtoken"],
    sensitive=True,
    metavar="BOXID",
    help="The yupptv.com boxid that's used in the BoxId cookie.",
)
@pluginargument(
    "yuppflixtoken",
    sensitive=True,
    metavar="YUPPFLIXTOKEN",
    help="The yupptv.com yuppflixtoken that's used in the YuppflixToken cookie.",
)
@pluginargument(
    "purge-credentials",
    action="store_true",
    help="Purge cached YuppTV credentials to initiate a new session and reauthenticate.",
)
class YuppTV(Plugin):
    _cookie_expiry = 3600 * 24 * 365

    def _login_using_box_id_and_yuppflix_token(self, box_id, yuppflix_token):
        time_now = time.time()

        self.session.http.cookies.set(
            "BoxId",
            box_id,
            domain="www.yupptv.com",
            path="/",
            expires=time_now + self._cookie_expiry,
        )
        self.session.http.cookies.set(
            "YuppflixToken",
            yuppflix_token,
            domain="www.yupptv.com",
            path="/",
            expires=time_now + self._cookie_expiry,
        )

        self.save_cookies()
        log.info("Successfully set BoxId and YuppflixToken")

    def _get_streams(self):
        self.session.http.headers.update({"User-Agent": useragents.CHROME})
        self.session.http.headers.update({"Origin": "https://www.yupptv.com"})

        authed = (
            self.session.http.cookies.get("BoxId")
            and self.session.http.cookies.get("YuppflixToken")
        )  # fmt: skip

        login_box_id = self.get_option("boxid")
        login_yuppflix_token = self.get_option("yuppflixtoken")

        if self.options.get("purge_credentials"):
            self.clear_cookies()
            authed = False
            log.info("All credentials were successfully removed")

        if authed:
            log.debug("Attempting to authenticate using cached cookies")
        elif login_box_id and login_yuppflix_token:
            self._login_using_box_id_and_yuppflix_token(
                login_box_id,
                login_yuppflix_token,
            )
            authed = True

        page = self.session.http.get(self.url)
        if authed and "btnsignup" in page.text:
            log.error("This device requires renewed credentials to log in")
            return

        match = re.search(r"""src:\s*(?P<q>["'])(?P<url>.+?)(?P=q)""", page.text)
        if not match or "preview/" in match["url"]:
            if "btnsignup" in page.text:
                log.error("This stream requires you to login")
            else:
                log.error("This stream requires a subscription")
            return

        def override_encoding(res, *_, **__):
            res.encoding = "utf-8"

        return HLSStreamYupptv.parse_variant_playlist(
            self.session,
            match["url"],
            hooks={"response": override_encoding},
        )


__plugin__ = YuppTV
