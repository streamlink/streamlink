import base64
import re
import sys
import time

from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA

import streamlink
from streamlink.plugin import Plugin, PluginArguments, PluginArgument
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.plugin.api.validate import Schema
from streamlink.stream.dash import DASHStream
from streamlink_cli.console import ConsoleOutput


class SteamLoginFailed(Exception):
    pass


class SteamBroadcastPlugin(Plugin):
    _url_re = re.compile(r"https?://steamcommunity.com/broadcast/watch/(\d+)")
    _get_broadcast_url = "http://steamcommunity.com/broadcast/getbroadcastmpd/"
    _user_agent = "streamlink/{}".format(streamlink.__version__)
    _broadcast_schema = Schema({
        "success": validate.any("ready", "unavailable", "waiting", "waiting_to_start"),
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
            required=True,
            help="""
            A Steam account email address to access friends/private streams
            """
        ),
        PluginArgument(
            "password",
            metavar="PASSWORD",
            required=True,
            sensitive=True,
            help="""
            A Steam account password to use with --steam-email.
            """
    ))

    def __init__(self, url):
        super(SteamBroadcastPlugin, self).__init__(url)
        http.headers["User-Agent"] = self._user_agent
        self.console = ConsoleOutput(sys.stdout, self.session)

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

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
        res = http.get(self._get_rsa_key_url, params=dict(username=email, donotcache=self.donotcache))
        rsadata = http.json(res, schema=self._rsa_key_schema)

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

        res = http.post(self._dologin_url, data=login_data)

        resp = http.json(res, schema=self._dologin_schema)

        if not resp[u"success"]:
            if resp.get(u"captcha_needed"):
                # special case for captcha
                captchagid = resp[u"captcha_gid"]
                self.logger.error("Captcha result required, open this URL to see the captcha: {}".format(
                    self._captcha_url.format(captchagid)))
                captcha_text = self.console.ask("Captcha text: ")
                if not captcha_text:
                    return False
            else:
                # If the user must enter the code that was emailed to them
                if resp.get(u"emailauth_needed"):
                    if not emailauth:
                        emailauth = self.console.ask("Email auth code required: ")
                        if not emailauth:
                            return False
                    else:
                        raise SteamLoginFailed("Email auth key error")

                # If the user must enter a two factor auth code
                if resp.get(u"requires_twofactor"):
                    twofactorcode = self.console.ask("Two factor auth code required: ")
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
            self.logger.error("Something when wrong when logging in to Steam")
            return False

    def login(self, email, password):
        self.logger.info("Attempting to login to Steam as {}".format(email))
        return self.dologin(email, password)

    def _get_broadcast_stream(self, steamid, viewertoken=0):
        res = http.get(self._get_broadcast_url,
                       params=dict(broadcastid=0,
                                   steamid=steamid,
                                   viewertoken=viewertoken))
        return http.json(res, schema=self._broadcast_schema)

    def _get_streams(self):
        streamdata = None
        if self.login(self.options.get("email"), self.options.get("password")):
            # extract the steam ID from the URL
            steamid = self._url_re.match(self.url).group(1)

            while streamdata is None or streamdata[u"success"] in ("waiting", "waiting_for_start"):
                streamdata = self._get_broadcast_stream(steamid)

                if streamdata[u"success"] == "ready":
                    return DASHStream.parse_manifest(self.session, streamdata["url"])
                elif streamdata[u"success"] == "unavailable":
                    self.logger.error("This stream is currently unavailable")
                    return
                else:
                    r = streamdata[u"retry"] / 1000.0
                    self.logger.info("Waiting for stream, will retry again in {} seconds...".format(r))
                    time.sleep(r)


__plugin__ = SteamBroadcastPlugin
