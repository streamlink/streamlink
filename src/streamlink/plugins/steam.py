import base64
import logging
import re
import time

from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA

import streamlink
from streamlink.exceptions import FatalPluginError
from streamlink.plugin import Plugin, PluginArguments, PluginArgument
from streamlink.plugin.api import validate
from streamlink.plugin.api.utils import itertags, parse_json
from streamlink.plugin.api.validate import Schema
from streamlink.stream.dash import DASHStream
from streamlink.compat import html_unescape

log = logging.getLogger(__name__)


class SteamLoginFailed(Exception):
    pass


class SteamBroadcastPlugin(Plugin):
    _url_re = re.compile(r"https?://steamcommunity.com/broadcast/watch/(\d+)")
    _steamtv_url_re = re.compile(r"https?://steam.tv/(\w+)")
    _watch_broadcast_url = "https://steamcommunity.com/broadcast/watch/"
    _get_broadcast_url = "https://steamcommunity.com/broadcast/getbroadcastmpd/"
    _user_agent = "streamlink/{}".format(streamlink.__version__)
    _broadcast_schema = Schema({
        "success": validate.any("ready", "unavailable", "waiting", "waiting_to_start", "waiting_for_start"),
        "retry": int,
        "broadcastid": validate.any(validate.text, int),
        validate.optional("url"): validate.url(),
        validate.optional("viewertoken"): validate.text
    })
    _get_rsa_key_url = "https://steamcommunity.com/login/getrsakey/"
    _rsa_key_schema = validate.Schema({
        "publickey_exp": validate.all(validate.text, validate.transform(lambda x: int(x, 16))),
        "publickey_mod": validate.all(validate.text, validate.transform(lambda x: int(x, 16))),
        "success": True,
        "timestamp": validate.text,
        "token_gid": validate.text
    })
    _dologin_url = "https://steamcommunity.com/login/dologin/"
    _dologin_schema = validate.Schema({
        "success": bool,
        "requires_twofactor": bool,
        validate.optional("message"): validate.text,
        validate.optional("emailauth_needed"): bool,
        validate.optional("emaildomain"): validate.text,
        validate.optional("emailsteamid"): validate.text,
        validate.optional("login_complete"): bool,
        validate.optional("captcha_needed"): bool,
        validate.optional("captcha_gid"): validate.any(validate.text, int)
    })
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

    def __init__(self, url):
        super(SteamBroadcastPlugin, self).__init__(url)
        self.session.http.headers["User-Agent"] = self._user_agent

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None or cls._steamtv_url_re.match(url) is not None

    @property
    def donotcache(self):
        return str(int(time.time() * 1000))

    def encrypt_password(self, email, password):
        """
        Get the RSA key for the user and encrypt the users password
        :param email: steam account
        :param password: password for account
        :return: encrypted password
        """
        res = self.session.http.get(self._get_rsa_key_url, params=dict(username=email, donotcache=self.donotcache))
        rsadata = self.session.http.json(res, schema=self._rsa_key_schema)

        rsa = RSA.construct((rsadata["publickey_mod"], rsadata["publickey_exp"]))
        cipher = PKCS1_v1_5.new(rsa)
        return base64.b64encode(cipher.encrypt(password.encode("utf8"))), rsadata["timestamp"]

    def dologin(self, email, password, emailauth="", emailsteamid="", captchagid="-1", captcha_text="", twofactorcode=""):
        """
        Logs in to Steam

        """
        epassword, rsatimestamp = self.encrypt_password(email, password)

        login_data = {
            'username': email,
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

        res = self.session.http.post(self._dologin_url, data=login_data)

        resp = self.session.http.json(res, schema=self._dologin_schema)

        if not resp[u"success"]:
            if resp.get(u"captcha_needed"):
                # special case for captcha
                captchagid = resp[u"captcha_gid"]
                log.error("Captcha result required, open this URL to see the captcha: {}".format(
                    self._captcha_url.format(captchagid)))
                try:
                    captcha_text = self.input_ask("Captcha text")
                except FatalPluginError:
                    captcha_text = None
                if not captcha_text:
                    return False
            else:
                # If the user must enter the code that was emailed to them
                if resp.get(u"emailauth_needed"):
                    if not emailauth:
                        try:
                            emailauth = self.input_ask("Email auth code required")
                        except FatalPluginError:
                            emailauth = None
                        if not emailauth:
                            return False
                    else:
                        raise SteamLoginFailed("Email auth key error")

                # If the user must enter a two factor auth code
                if resp.get(u"requires_twofactor"):
                    try:
                        twofactorcode = self.input_ask("Two factor auth code required")
                    except FatalPluginError:
                        twofactorcode = None
                    if not twofactorcode:
                        return False

                if resp.get(u"message"):
                    raise SteamLoginFailed(resp[u"message"])

            return self.dologin(email, password,
                                emailauth=emailauth,
                                emailsteamid=resp.get(u"emailsteamid", u""),
                                captcha_text=captcha_text,
                                captchagid=captchagid,
                                twofactorcode=twofactorcode)
        elif resp.get("login_complete"):
            return True
        else:
            log.error("Something when wrong when logging in to Steam")
            return False

    def login(self, email, password):
        log.info("Attempting to login to Steam as {}".format(email))
        return self.dologin(email, password)

    def _get_broadcast_stream(self, steamid, viewertoken=0, sessionid=None):
        log.debug("Getting broadcast stream: sessionid={0}".format(sessionid))
        res = self.session.http.get(self._get_broadcast_url,
                                    params=dict(broadcastid=0,
                                                steamid=steamid,
                                                viewertoken=viewertoken,
                                                sessionid=sessionid))
        return self.session.http.json(res, schema=self._broadcast_schema)

    def _get_streams(self):
        streamdata = None
        if self.get_option("email"):
            if self.login(self.get_option("email"), self.get_option("password")):
                log.info("Logged in as {0}".format(self.get_option("email")))
                self.save_cookies(lambda c: "steamMachineAuth" in c.name)

        # Handle steam.tv URLs
        if self._steamtv_url_re.match(self.url) is not None:
            # extract the steam ID from the page
            res = self.session.http.get(self.url)
            for div in itertags(res.text, 'div'):
                if div.attributes.get("id") == "webui_config":
                    broadcast_data = html_unescape(div.attributes.get("data-broadcast"))
                    steamid = parse_json(broadcast_data).get("steamid")
                    self.url = self._watch_broadcast_url + steamid

        # extract the steam ID from the URL
        steamid = self._url_re.match(self.url).group(1)
        res = self.session.http.get(self.url)  # get the page to set some cookies
        sessionid = res.cookies.get('sessionid')

        while streamdata is None or streamdata[u"success"] in ("waiting", "waiting_for_start"):
            streamdata = self._get_broadcast_stream(steamid,
                                                    sessionid=sessionid)

            if streamdata[u"success"] == "ready":
                return DASHStream.parse_manifest(self.session, streamdata["url"])
            elif streamdata[u"success"] == "unavailable":
                log.error("This stream is currently unavailable")
                return
            else:
                r = streamdata[u"retry"] / 1000.0
                log.info("Waiting for stream, will retry again in {} seconds...".format(r))
                time.sleep(r)


__plugin__ = SteamBroadcastPlugin
