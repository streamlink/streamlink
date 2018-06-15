import re
import time
from uuid import uuid4

from streamlink.compat import quote
from streamlink.plugin import Plugin, PluginArguments, PluginArgument
from streamlink.plugin.api import http, useragents
from streamlink.stream import HLSStream
from streamlink.utils import url_equal


class BTSports(Plugin):
    url_re = re.compile(r"https?://sport.bt.com")

    arguments = PluginArguments(
        PluginArgument(
            "email",
            requires=["password"],
            metavar="EMAIL",
            required=True,
            help="""
            The email associated with your BT Sport account, required to access any
            BT Sport stream.
            """

        ),
        PluginArgument(
            "password",
            sensitive=True,
            metavar="PASSWORD",
            help="Your BT Sport account password."
        )
    )

    content_re = re.compile(r"CONTENT_(\w+)\s*=\s*'(\w+)'")
    saml_re = re.compile(r'''name="SAMLResponse" value="(.*?)"''', re.M | re.DOTALL)
    api_url = "https://be.avs.bt.com/AVS/besc"
    saml_url = "https://samlfed.bt.com/sportgetfedwebhls"
    login_url = "https://signin1.bt.com/siteminderagent/forms/login.fcc"

    def __init__(self, url):
        super(BTSports, self).__init__(url)
        http.headers = {"User-Agent": useragents.FIREFOX}

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def login(self, username, password):
        self.logger.debug("Logging in as {0}".format(username))

        redirect_to = "https://home.bt.com/ss/Satellite/secure/loginforward?redirectURL={0}".format(quote(self.url))
        data = {
            "cookieExpp": "30",
            "Switch": "yes",
            "SMPostLoginUrl": "/appsyouraccount/secure/postlogin",
            "loginforward": "https://home.bt.com/ss/Satellite/secure/loginforward",
            "smauthreason": "0",
            "TARGET": redirect_to,
            "USER": username,
            "PASSWORD": password}

        res = http.post(self.login_url, data=data)

        self.logger.debug("Redirected to: {0}".format(res.url))


        if url_equal(res.url, self.url, ignore_scheme=True):
            self.logger.debug("Login successful, getting SAML token")
            res = http.get("https://samlfed.bt.com/sportgetfedwebhls?bt.cid={0}".format(self.acid()))
            d = self.saml_re.search(res.text)
            if d:
                saml_data = d.group(1)
                self.logger.debug("BT Sports federated login...")
                res = http.post(self.api_url,
                                params={"action": "LoginBT", "channel": "WEBHLS", "bt.cid": self.acid},
                                data={"SAMLResponse": saml_data})
                fed_json = http.json(res)
                success = fed_json['resultCode'] == "OK"
                if not success:
                    self.logger.error("Failed to login: {0} - {1}".format(fed_json['errorDescription'],
                                                                          fed_json['message']))
                return success
        return False

    def device_id(self):
        device_id = self.cache.get("device_id") or str(uuid4())
        self.cache.set("device_id", device_id)
        return device_id

    def acid(self):
        acid = self.cache.get("acid") or "{cid}-B-{timestamp}".format(cid=self.device_id(), timestamp=int(time.time()))
        self.cache.set("acid", acid)
        return acid

    def _get_cdn(self, channel_id, channel_type="LIVE"):
        d = {"action": "GetCDN",
             "type": channel_type,
             "id": channel_id,
             "channel": "WEBHLS",
             "asJson": "Y",
             "bt.cid": self.acid(),
             "_": int(time.time())}

        res = http.get(self.api_url, params=d, headers={"Accept": "application/json"})
        return http.json(res)

    def _get_streams(self):
        if self.options.get("email") and self.options.get("password"):
            if self.login(self.options.get("email"), self.options.get("password")):
                self.logger.debug("Logged in and authenticated with BT Sports.")

                res = http.get(self.url)
                m = self.content_re.findall(res.text)
                if m:
                    info = dict(m)
                    data = self._get_cdn(info.get("ID"), info.get("TYPE"))
                    if data['resultCode'] == 'OK':
                        return HLSStream.parse_variant_playlist(self.session, data['resultObj']['src'])
                    else:
                        self.logger.error("Failed to get stream with error: {0} - {1}".format(data['errorDescription'],
                                                                                              data['message']))
        else:
            self.logger.error("A username and password is required to use BT Sports")

__plugin__ = BTSports
