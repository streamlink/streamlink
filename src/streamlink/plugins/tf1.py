"""
$description French live TV channels from TF1 Group, including LCI and TF1.
$url tf1.fr
$url tf1info.fr
$url lci.fr
$type live
$region France
"""

import json
import logging
import re

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import useragents, validate
from streamlink.plugin.plugin import pluginargument
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?
    (?:
        tf1\.fr/(?:
            (?P<live>[\w-]+)/direct/?
            |
            stream/(?P<stream>[\w-]+)
        )
        |
        (?P<lci>tf1info|lci)\.fr/direct/?
    )
""", re.VERBOSE))
@pluginargument(
    "username",
    required=True,
    requires=["password"],
    metavar="USERNAME",
    help="Your TF1 account username",
)
@pluginargument(
    "password",
    required=True,
    sensitive=True,
    metavar="PASSWORD",
    help="Your TF1 account password",
)

class TF1(Plugin):
    _URL_API = "https://mediainfo.tf1.fr/mediainfocombo/{channel_id}"
    # Necessary for login.
    auth_url = "https://compte.tf1.fr/accounts.login"
    session_url = "https://www.tf1.fr/token/gigya/web"
    gigya_api_key = '3_hWgJdARhz_7l1oOp3a8BDLoR9cuWZpUaKG4aqF7gum9_iK3uTZ2VlDBl8ANf8FVk'


    def _get_channel(self):
        if self.match["live"]:
            channel = self.match["live"]
            channel_id = f"L_{channel.upper()}"
        elif self.match["lci"]:
            channel = "LCI"
            channel_id = "L_LCI"
        elif self.match["stream"]:
            channel = self.match["stream"]
            channel_id = f"L_FAST_v2l-{channel}"
        else:  # pragma: no cover
            raise PluginError("Invalid channel")

        return channel, channel_id

    def _api_call(self, channel_id):
        return self.session.http.get(
            self._URL_API.format(channel_id=channel_id),
            params={
                "pver": "5015000",
                "context": "MYTF1"
            },
            headers={
                # forces HLS streams
                "User-Agent": "iPhone",
                "authorization": "Bearer {token}".format(token=self.user_token)
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "delivery": validate.any(
                        validate.all(
                            {
                                "code": 200,
                                "format": "hls",
                                "url": validate.url(),
                            },
                            validate.union_get("code", "url"),
                        ),
                        validate.all(
                            {
                                "code": int,
                                "error": str,
                            },
                            validate.union_get("code", "error"),
                        ),
                    ),
                },
                validate.get("delivery"),
            ),
        )
    
    def login(self, username, password):
        """
        Create session using Gigya's API for TF1.
        :return: Whether authentication was successful
        :rtype: bool
        """

        def auth_check():
            res = self.session.http.post(
            self.auth_url,
            data=dict(
                loginID=username,
                password=password,
                APIKey=self.gigya_api_key,
                includeUserInfo="true"
            ),
            headers={"Referer": self.url, "User-Agent": useragents.IPHONE})

            # If TF1 login is successful, get Gigya token.
            if res.status_code == 200:
                # make the session request to get the correct cookies
                session_res = self.session.http.post(
                    self.session_url,
                    data=json.dumps({
                        "uid": res.json()['userInfo']['UID'],
                        "signature": res.json()['userInfo']['UIDSignature'],
                        "timestamp": int(res.json()['userInfo']['signatureTimestamp']),
                        "consent_ids": ["1", "2", "3", "4", "10001", "10003", "10005", "10007", "10013", "10015", "10017", "10019", "10009", "10011", "13002", "13001", "10004", "10014", "10016", "10018", "10020", "10010", "10012", "10006", "10008"]
                    })
                )
                if session_res.status_code == 200:
                    self.user_token = session_res.json()['token']
                    return True
                else:
                    return False
            else:
                return False

        
        if auth_check() == True:
            log.debug("Already authenticated, skipping authentication")
            return True
        else:
            return False

    def _get_streams(self):
        if not self.login(self.get_option("username"), self.get_option("password")):
            log.error("Failed to login, check username and password")
            return

        channel, channel_id = self._get_channel()
        log.debug(f"Found channel {channel} ({channel_id})")

        code, data = self._api_call(channel_id)
        if code != 200:
            log.error(data)
            return

        return HLSStream.parse_variant_playlist(self.session, data)


__plugin__ = TF1
