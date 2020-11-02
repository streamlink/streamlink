import logging
import re
import time
from urllib.parse import quote
from uuid import uuid4

from streamlink.plugin import Plugin, PluginArgument, PluginArguments
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class BTSports(Plugin):
    url_re = re.compile(r"https?://sport\.bt\.com")

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

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def login(self, username, password):
        log.debug("Logging in as {0}".format(username))

        redirect_to = "https://home.bt.com/ss/Satellite/secure/loginforward?view=btsport&redirectURL={0}".format(
            quote(self.url)
        )
        data = {
            "cookieExpp": "30",
            "Switch": "yes",
            "SMPostLoginUrl": "/appsyouraccount/secure/postlogin",
            "loginforward": "https://home.bt.com/ss/Satellite/secure/loginforward?view=btsport",
            "smauthreason": "0",
            "TARGET": redirect_to,
            "USER": username,
            "PASSWORD": password}
        res = self.session.http.post(self.login_url, data=data)

        log.debug("Redirected to: {0}".format(res.url))

        if "loginerror" not in res.text:
            log.debug("Login successful, getting SAML token")
            res = self.session.http.get("https://samlfed.bt.com/sportgetfedwebhls?bt.cid={0}".format(self.acid()))
            d = self.saml_re.search(res.text)
            if d:
                saml_data = d.group(1)
                log.debug("BT Sports federated login...")
                res = self.session.http.post(
                    self.api_url,
                    params={"action": "LoginBT", "channel": "WEBHLS", "bt.cid": self.acid},
                    data={"SAMLResponse": saml_data}
                )
                fed_json = self.session.http.json(res)
                success = fed_json['resultCode'] == "OK"
                if not success:
                    log.error("Failed to login: {0} - {1}".format(fed_json['errorDescription'], fed_json['message']))
                return success
        else:
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

        res = self.session.http.get(self.api_url, params=d, headers={"Accept": "application/json"})
        return self.session.http.json(res)

    @Plugin.broken(2946)
    def _get_streams(self):
        if self.options.get("email") and self.options.get("password"):
            if self.login(self.options.get("email"), self.options.get("password")):
                log.debug("Logged in and authenticated with BT Sports.")

                res = self.session.http.get(self.url)
                m = self.content_re.findall(res.text)
                if m:
                    info = dict(m)
                    data = self._get_cdn(info.get("ID"), info.get("TYPE"))
                    log.debug("CDN respsonse: {0}".format(data))
                    if data['resultCode'] == 'OK':
                        return HLSStream.parse_variant_playlist(self.session, data['resultObj']['src'])
                    else:
                        log.error("Failed to get stream with error: {0} - {1}".format(data['errorDescription'],
                                                                                      data['message']))
            else:
                log.error("Login failed.")
        else:
            log.error("A username and password is required to use BT Sports")


__plugin__ = BTSports
