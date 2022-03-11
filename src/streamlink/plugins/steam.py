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

from streamlink.compat import str
from streamlink.exceptions import FatalPluginError
from streamlink.plugin import Plugin, PluginArgument, PluginArguments, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream

log = logging.getLogger(__name__)


class SteamLoginFailed(Exception):
    pass


@pluginmatcher(re.compile(
    r"https?://steamcommunity\.com/broadcast/watch/(\d+)"
))
@pluginmatcher(re.compile(
    r"https?://steam\.tv/(\w+)"
))
class SteamBroadcastPlugin(Plugin):
    _watch_broadcast_url = "https://steamcommunity.com/broadcast/watch/{steamid}"
    _get_broadcast_url = "https://steamcommunity.com/broadcast/getbroadcastmpd/"
    _get_rsa_key_url = "https://steamcommunity.com/login/getrsakey/"
    _dologin_url = "https://steamcommunity.com/login/dologin/"
    _captcha_url = "https://steamcommunity.com/public/captcha.php?gid={}"

    arguments = PluginArguments(
        PluginArgument(
            "email",
            metavar="EMAIL",
            requires=["password"],
            help="""
            A Steam account email address to access friends/private streams
            """
        ),
        PluginArgument(
            "password",
            metavar="PASSWORD",
            sensitive=True,
            help="""
            A Steam account password to use with --steam-email.
            """
        ))

    def encrypt_password(self, email, password):
        """
        Get the RSA key for the user and encrypt the users password
        :param email: steam account
        :param password: password for account
        :return: encrypted password
        """
        rsadata = self.session.http.get(
            self._get_rsa_key_url,
            params=dict(
                username=email,
                donotcache=str(int(time.time() * 1000))
            ),
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "publickey_exp": validate.all(validate.text, validate.transform(lambda x: int(x, 16))),
                    "publickey_mod": validate.all(validate.text, validate.transform(lambda x: int(x, 16))),
                    "success": True,
                    "timestamp": validate.text,
                    "token_gid": validate.text
                }
            )
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
            "twofactorcode": twofactorcode
        }

        resp = self.session.http.post(
            self._dologin_url,
            data=login_data,
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "success": bool,
                    "requires_twofactor": bool,
                    validate.optional("message"): validate.text,
                    validate.optional("emailauth_needed"): bool,
                    validate.optional("emaildomain"): validate.text,
                    validate.optional("emailsteamid"): validate.text,
                    validate.optional("login_complete"): bool,
                    validate.optional("captcha_needed"): bool,
                    validate.optional("captcha_gid"): validate.any(validate.text, int)
                }
            )
        )

        if resp.get("login_complete"):
            return True

        if not resp["success"]:
            if resp.get("captcha_needed"):
                # special case for captcha
                captchagid = resp["captcha_gid"]
                captchaurl = self._captcha_url.format(captchagid)
                log.error("Captcha result required, open this URL to see the captcha: {}".format(
                    captchaurl))
                try:
                    captcha_text = self.input_ask("Captcha text")
                except FatalPluginError:
                    captcha_text = None
                if not captcha_text:
                    return False
            else:
                # If the user must enter the code that was emailed to them
                if resp.get("emailauth_needed"):
                    if emailauth:
                        raise SteamLoginFailed("Email auth key error")
                    try:
                        emailauth = self.input_ask("Email auth code required")
                    except FatalPluginError:
                        emailauth = None
                    if not emailauth:
                        return False

                # If the user must enter a two factor auth code
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
                twofactorcode=twofactorcode
            )

        log.error("Something went wrong while logging in to Steam")
        return False

    def _get_broadcast_stream(self, steamid, viewertoken=0, sessionid=None):
        log.debug("Getting broadcast stream: sessionid={0}".format(sessionid))
        return self.session.http.get(
            self._get_broadcast_url,
            params=dict(
                broadcastid=0,
                steamid=steamid,
                viewertoken=viewertoken,
                sessionid=sessionid
            ),
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "success": validate.any("ready", "unavailable", "waiting", "waiting_to_start", "waiting_for_start"),
                    "retry": int,
                    "broadcastid": validate.any(validate.text, int),
                    validate.optional("url"): validate.url(),
                    validate.optional("viewertoken"): validate.text
                }
            )
        )

    def _find_steamid(self, url):
        return self.session.http.get(url, schema=validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string(".//div[@id='webui_config']/@data-broadcast"),
            validate.any(None, validate.all(
                validate.text,
                validate.parse_json(),
                {"steamid": validate.text},
                validate.get("steamid")
            ))
        ))

    def _get_streams(self):
        self.session.http.headers["User-Agent"] = "streamlink/{0}".format(self.session.version)

        email = self.get_option("email")
        if email:
            log.info("Attempting to login to Steam as {0}".format(email))
            if self.dologin(email, self.get_option("password")):
                log.info("Logged in as {0}".format(email))
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

        streamdata = None
        while streamdata is None or streamdata["success"] in ("waiting", "waiting_for_start"):
            streamdata = self._get_broadcast_stream(steamid, sessionid=sessionid)

            if streamdata["success"] == "ready":
                return DASHStream.parse_manifest(self.session, streamdata["url"])

            if streamdata["success"] == "unavailable":
                log.error("This stream is currently unavailable")
                return

            r = streamdata["retry"] / 1000.0
            log.info("Waiting for stream, will retry again in {0:.1f} seconds...".format(r))
            time.sleep(r)


__plugin__ = SteamBroadcastPlugin
