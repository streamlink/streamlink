import logging
import re
import time

from streamlink.plugin import Plugin, PluginArgument, PluginArguments
from streamlink.plugin.api import useragents
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class YuppTV(Plugin):
    _url_re = re.compile(r'https?://(?:www\.)?yupptv\.com')
    _m3u8_re = re.compile(r'''['"](http.+\.m3u8.*?)['"]''')
    _cookie_expiry = 3600 * 24 * 365

    arguments = PluginArguments(
        PluginArgument(
            "boxid",
            requires=["yuppflixtoken"],
            sensitive=True,
            metavar="BOXID",
            help="""
        The yupptv.com boxid that's used in the BoxId cookie.
        Can be used instead of the username/password login process.
        """),
        PluginArgument(
            "yuppflixtoken",
            sensitive=True,
            metavar="YUPPFLIXTOKEN",
            help="""
        The yupptv.com yuppflixtoken that's used in the YuppflixToken cookie.
        Can be used instead of the username/password login process.
        """),
        PluginArgument(
            "purge-credentials",
            action="store_true",
            help="""
        Purge cached YuppTV credentials to initiate a new session
        and reauthenticate.
        """),
    )

    def __init__(self, url):
        super().__init__(url)
        self._authed = (self.session.http.cookies.get("BoxId")
                        and self.session.http.cookies.get("YuppflixToken"))

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

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

        login_box_id = self.get_option("boxid")
        login_yuppflix_token = self.get_option("yuppflixtoken")

        if self.options.get("purge_credentials"):
            self.clear_cookies()
            self._authed = False
            log.info("All credentials were successfully removed")

        if self._authed:
            log.debug("Attempting to authenticate using cached cookies")
        elif not self._authed and login_box_id and login_yuppflix_token:
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

            return HLSStream.parse_variant_playlist(self.session, stream_url)
        elif "btnsignup" in page.text:
            log.error("This stream requires you to login")
        elif "btnsubscribe" in page.text:
            log.error("This stream requires a subscription")


__plugin__ = YuppTV
