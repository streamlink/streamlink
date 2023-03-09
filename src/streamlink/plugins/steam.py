"""
$description Live streaming video game broadcasts from the Steam gaming community.
$url steamcommunity.com
$url steam.tv
$type live
$account Some streams require a login
"""

import base64
import logging
import re
import time

from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA

from streamlink.exceptions import FatalPluginError
from streamlink.plugin import Plugin, pluginargument, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream


log = logging.getLogger(__name__)


class SteamLoginFailed(Exception):
    pass


@pluginmatcher(re.compile(
    r"https?://steamcommunity\.com/broadcast/watch/(\d+)",
))
@pluginmatcher(re.compile(
    r"https?://steam\.tv/(\w+)",
))
@pluginargument(
    "email",
    requires=["password"],
    metavar="EMAIL",
    help="A Steam account email address to access friends/private streams",
)
@pluginargument(
    "password",
    sensitive=True,
    metavar="PASSWORD",
    help="A Steam account password to use with --steam-email.",
)
class SteamBroadcastPlugin(Plugin):
    _watch_broadcast_url = "https://steamcommunity.com/broadcast/watch/{steamid}"
    _get_broadcast_url = "https://steamcommunity.com/broadcast/getbroadcastmpd/"
    _get_rsa_key_url = "https://steamcommunity.com/login/getrsakey/"
    _dologin_url = "https://steamcommunity.com/login/dologin/"
    _captcha_url = "https://steamcommunity.com/public/captcha.php?gid={}"

    @property
    def donotcache(self):
        return str(int(time.time() * 1000))

    def encrypt_password(self, email, password):
        """
        Get the RSA key for the user and encrypt the user's password
        :param email: steam account
        :param password: password for account
        :return: encrypted password
        """
        rsadata = self.session.http.get(
            self._get_rsa_key_url,
            params=dict(
                username=email,
                donotcache=self.donotcache,
            ),
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "publickey_exp": validate.all(str, validate.transform(lambda x: int(x, 16))),
                    "publickey_mod": validate.all(str, validate.transform(lambda x: int(x, 16))),
                    "success": True,
                    "timestamp": str,
                    "token_gid": str,
                },
            ),
        )

        rsa = RSA.construct((rsadata["publickey_mod"], rsadata["publickey_exp"]))
        cipher = PKCS1_v1_5.new(rsa)
        return base64.b64encode(cipher.encrypt(password.encode("utf8"))), rsadata["timestamp"]

    def dologin(self, email, password, emailauth="", emailsteamid="", captchagid="-1", captcha_text="", twofactorcode=""):
        epassword, rsatimestamp = self.encrypt_password(email, password)

        login_data = {
            "username": email,
            "password": epassword,
            "emailauth": emailauth,
            "loginfriendlyname": "Streamlink",
            "captchagid": captchagid,
            "captcha_text": captcha_text,
            "emailsteamid": emailsteamid,
            "rsatimestamp": rsatimestamp,
            "remember_login": True,
            "donotcache": self.donotcache,
            "twofactorcode": twofactorcode,
        }

        resp = self.session.http.post(
            self._dologin_url,
            data=login_data,
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "success": bool,
                    "requires_twofactor": bool,
                    validate.optional("message"): str,
                    validate.optional("emailauth_needed"): bool,
                    validate.optional("emaildomain"): str,
                    validate.optional("emailsteamid"): str,
                    validate.optional("login_complete"): bool,
                    validate.optional("captcha_needed"): bool,
                    validate.optional("captcha_gid"): validate.any(str, int),
                },
            ),
        )

        if resp.get("login_complete"):
            return True

        if not resp["success"]:
            if resp.get("captcha_needed"):
                # special case for captcha
                captchagid = resp["captcha_gid"]
                captchaurl = self._captcha_url.format(captchagid)
                log.error(f"Captcha result required, open this URL to see the captcha: {captchaurl}")
                try:
                    captcha_text = self.input_ask("Captcha text")
                except FatalPluginError:
                    captcha_text = None
                if not captcha_text:
                    return False
            else:
                # Whether the user must enter the code that was emailed to them
                if resp.get("emailauth_needed"):
                    if emailauth:
                        raise SteamLoginFailed("Email auth key error")
                    try:
                        emailauth = self.input_ask("Email auth code required")
                    except FatalPluginError:
                        emailauth = None
                    if not emailauth:
                        return False

                # Whether the user must enter a two-factor auth code
                if resp.get("requires_twofactor"):
                    try:
                        twofactorcode = self.input_ask("Two factor auth code required")
                    except FatalPluginError:
                        twofactorcode = None
                    if not twofactorcode:
                        return False

                if resp.get("message"):
                    raise SteamLoginFailed(resp["message"])

            return self.dologin(
                email,
                password,
                emailauth=emailauth,
                emailsteamid=resp.get("emailsteamid", ""),
                captcha_text=captcha_text,
                captchagid=captchagid,
                twofactorcode=twofactorcode,
            )

        log.error("Something went wrong while logging in to Steam")
        return False

    def _get_broadcast_stream(self, steamid, viewertoken=0, sessionid=None):
        log.debug(f"Getting broadcast stream: sessionid={sessionid}")
        return self.session.http.get(
            self._get_broadcast_url,
            params=dict(
                broadcastid=0,
                steamid=steamid,
                viewertoken=viewertoken,
                sessionid=sessionid,
            ),
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "success": str,
                    validate.optional("url"): validate.url(),
                    validate.optional("cdn_auth_url_parameters"): validate.any(str, None),
                },
                validate.union_get("success", "url", "cdn_auth_url_parameters"),
            ),
        )

    def _find_steamid(self, url):
        return self.session.http.get(url, schema=validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string(".//div[@id='webui_config']/@data-broadcast"),
            validate.none_or_all(
                validate.parse_json(),
                {"steamid": str},
                validate.get("steamid"),
            ),
        ))

    def _get_streams(self):
        self.session.http.headers["User-Agent"] = f"streamlink/{self.session.version}"

        email = self.get_option("email")
        if email:
            log.info(f"Attempting to login to Steam as {email}")
            try:
                success = self.dologin(email, self.get_option("password"))
            except SteamLoginFailed as err:
                log.error(err)
                return
            if success:
                log.info(f"Logged in as {email}")
                self.save_cookies(lambda c: "steamMachineAuth" in c.name)

        if self.matches[1] is None:
            steamid = self.match.group(1)
        else:
            steamid = self._find_steamid(self.url)
            if not steamid:
                return
            self.url = self._watch_broadcast_url.format(steamid=steamid)

        res = self.session.http.get(self.url)  # get the page to set some cookies
        sessionid = res.cookies.get("sessionid")

        success, url, cdn_auth = self._get_broadcast_stream(steamid, sessionid=sessionid)
        if success != "ready" or not url:
            log.error("This stream is currently unavailable")
            return

        # CDN auth data is only required at certain times of the day, and it makes
        # segment requests fail if missing (the DASH manifest still works regardless).
        # Remove leading ampersand and pass the params as a string, to avoid URL quoting.
        params = re.sub(r"^&", "", cdn_auth) if cdn_auth else None

        return DASHStream.parse_manifest(self.session, url, params=params)


__plugin__ = SteamBroadcastPlugin
