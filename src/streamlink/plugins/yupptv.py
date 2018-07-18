import logging
import re

from streamlink import PluginError
from streamlink.plugin import Plugin, PluginArguments, PluginArgument
from streamlink.plugin.api import useragents
from streamlink.stream import HLSStream



log = logging.getLogger(__name__)


class YuppTV(Plugin):
    _url_re = re.compile(r"""https?://(?:www\.)?yupptv\.com""", re.VERBOSE)
    _m3u8_re = re.compile(r'''['"](http.+\.m3u8.*?)['"]''')
    _login_url = "https://www.yupptv.com/auth/validateSignin"
    _box_logout = "https://www.yupptv.com/auth/confirmLogout"
    _signin_url = "https://www.yupptv.com/signin/"
    _account_url = "https://www.yupptv.com/account/myaccount.aspx"

    arguments = PluginArguments(
        PluginArgument(
            "email",
            requires=["password"],
            metavar="EMAIL",
            help="Your YuppTV account email"
        ),
        PluginArgument(
            "password",
            sensitive=True,
            metavar="PASSWORD",
            help="Your YuppTV account password."
        )
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def login(self, username, password, depth=3):
        if depth == 0:
            log.error("Failed to login to YuppTV")
            raise PluginError("cannot login")

        res = self.session.http.post(self._login_url, data=dict(user=username, password=password, isMobile=0), headers={"Referer": self._signin_url})
        data = self.session.http.json(res)
        resp = data['Response']
        if resp["tempBoxid"]:
            # log out on other device
            log.info("Logging out on other device: {0}".format(resp["tempBoxid"]))
            _ = self.session.http.get(self._box_logout, params=dict(boxId=resp["tempBoxid"]))
            return self.login(username, password, depth-1)
        return resp['errorCode'], resp['statusmsg']

    def _get_streams(self):
        self.session.http.headers.update({"User-Agent": useragents.CHROME})

        if self.get_option("email") and self.get_option("password"):
            error_code, error_msg = self.login(self.get_option("email"), self.get_option("password"))
            if error_code is None:
                log.info("Logged in as {0}".format(self.get_option("email")))
            else:
                log.error("Failed to login: {1} (code: {0})".format(error_code, error_msg))

        page = self.session.http.get(self.url)
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
