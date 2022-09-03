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
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r'https?://(?:www\.)?yupptv\.com'
))
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
    _m3u8_re = re.compile(r'''['"](http.+\.m3u8.*?)['"]''')
    _cookie_expiry = 3600 * 24 * 365

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._authed = (self.session.http.cookies.get("BoxId")
                        and self.session.http.cookies.get("YuppflixToken"))

    @staticmethod
    def _override_encoding(res, **kwargs):
        res.encoding = "utf-8"

    def _login_using_box_id_and_yuppflix_token(self, box_id, yuppflix_token):
        time_now = time.time()

        self.session.http.cookies.set(
            'BoxId',
            box_id,
            domain='www.yupptv.com',
            path='/',
            expires=time_now + self._cookie_expiry,
        )
        self.session.http.cookies.set(
            'YuppflixToken',
            yuppflix_token,
            domain='www.yupptv.com',
            path='/',
            expires=time_now + self._cookie_expiry,
        )

        self.save_cookies()
        log.info("Successfully set BoxId and YuppflixToken")

    def _get_streams(self):
        self.session.http.headers.update({"User-Agent": useragents.CHROME})
        self.session.http.headers.update({"Origin": "https://www.yupptv.com"})

        login_box_id = self.get_option("boxid")
        login_yuppflix_token = self.get_option("yuppflixtoken")

        if self.options.get("purge_credentials"):
            self.clear_cookies()
            self._authed = False
            log.info("All credentials were successfully removed")

        if self._authed:
            log.debug("Attempting to authenticate using cached cookies")
        elif login_box_id and login_yuppflix_token:
            self._login_using_box_id_and_yuppflix_token(
                login_box_id,
                login_yuppflix_token,
            )
            self._authed = True

        page = self.session.http.get(self.url)
        if self._authed and "btnsignup" in page.text:
            log.error("This device requires renewed credentials to log in")
            return

        match = self._m3u8_re.search(page.text)
        if match:
            stream_url = match.group(1)
            if "preview/" in stream_url:
                if "btnsignup" in page.text:
                    log.error("This stream requires you to login")
                else:
                    log.error("This stream requires a subscription")
                return

            return HLSStream.parse_variant_playlist(self.session,
                                                    stream_url,
                                                    hooks={"response": self._override_encoding})
        elif "btnsignup" in page.text:
            log.error("This stream requires you to login")
        elif "btnsubscribe" in page.text:
            log.error("This stream requires a subscription")


__plugin__ = YuppTV
