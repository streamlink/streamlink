import re

from streamlink.plugin import Plugin
from streamlink.plugin import PluginArguments, PluginArgument
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream

CHANNEL_API_URL = "http://live.afreecatv.com:8057/afreeca/player_live_api.php"
STREAM_INFO_URLS = "{rmd}/broad_stream_assign.html"

CHANNEL_RESULT_ERROR = 0
CHANNEL_RESULT_OK = 1

QUALITYS = ["original", "hd", "sd"]

QUALITY_WEIGHTS = {
    "original": 1080,
    "hd": 720,
    "sd": 480
}

_url_re = re.compile(r"http(s)?://(?P<cdn>\w+\.)?afreeca(tv)?\.com/(?P<username>\w+)(/\d+)?")

_channel_schema = validate.Schema(
    {
        "CHANNEL": {
            "RESULT": validate.transform(int),
            validate.optional("BPWD"): validate.text,
            validate.optional("BNO"): validate.text,
            validate.optional("RMD"): validate.text,
            validate.optional("AID"): validate.text,
            validate.optional("CDN"): validate.text
        }
    },
    validate.get("CHANNEL")
)

_stream_schema = validate.Schema(
    {
        validate.optional("view_url"): validate.url(
            scheme=validate.any("rtmp", "http")
        ),
        "stream_status": validate.text
    }
)


class AfreecaTV(Plugin):
    login_url = "https://member.afreecatv.com:8111/login/LoginAction.php"

    arguments = PluginArguments(
        PluginArgument(
            "username",
            requires=["password"],
            metavar="USERNAME",
            help="The username used to register with afreecatv.com."
        ),
        PluginArgument(
            "password",
            sensitive=True,
            metavar="PASSWORD",
            help="A afreecatv.com account password to use with --afreeca-username."
        )
    )

    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    @classmethod
    def stream_weight(cls, key):
        weight = QUALITY_WEIGHTS.get(key)
        if weight:
            return weight, "afreeca"

        return Plugin.stream_weight(key)

    def _get_channel_info(self, username):
        data = {
            "bid": username,
            "mode": "landing",
            "player_type": "html5"
        }

        res = http.post(CHANNEL_API_URL, data=data)
        return http.json(res, schema=_channel_schema)

    def _get_hls_key(self, broadcast, username, quality):
        headers = {
            "Referer": self.url
        }

        data = {
            "bid": username,
            "bno": broadcast,
            "pwd": "",
            "quality": quality,
            "type": "pwd"
        }
        res = http.post(CHANNEL_API_URL, data=data, headers=headers)
        return http.json(res, schema=_channel_schema)

    def _get_stream_info(self, broadcast, quality, cdn, rmd):
        params = {
            "return_type": cdn,
            "broad_key": "{broadcast}-flash-{quality}-hls".format(**locals())
        }
        res = http.get(STREAM_INFO_URLS.format(rmd=rmd), params=params)
        return http.json(res, schema=_stream_schema)

    def _get_hls_stream(self, broadcast, username, quality, cdn, rmd):
        keyjson = self._get_hls_key(broadcast, username, quality)

        if keyjson["RESULT"] != CHANNEL_RESULT_OK:
            return
        key = keyjson["AID"]

        info = self._get_stream_info(broadcast, quality, cdn, rmd)

        if "view_url" in info:
            return HLSStream(self.session, info["view_url"], params=dict(aid=key))

    def _login(self, username, password):
        data = {
            "szWork": "login",
            "szType": "json",
            "szUid": username,
            "szPassword": password,
            "isSaveId": "true",
            "isSavePw": "false",
            "isSaveJoin": "false"
        }

        res = http.post(self.login_url, data=data)
        res = http.json(res)
        if res["RESULT"] == 1:
            return True
        else:
            return False

    def _get_streams(self):
        if not self.session.get_option("hls-segment-ignore-names"):
            ignore_segment = ["_0", "_1", "_2"]
            self.session.set_option("hls-segment-ignore-names", ignore_segment)

        login_username = self.get_option("username")
        login_password = self.get_option("password")
        if login_username and login_password:
            self.logger.debug("Attempting login as {0}".format(login_username))
            if self._login(login_username, login_password):
                self.logger.info("Successfully logged in as {0}".format(login_username))
            else:
                self.logger.info("Failed to login as {0}".format(login_username))

        match = _url_re.match(self.url)
        username = match.group("username")

        channel = self._get_channel_info(username)
        if channel.get("BPWD") == "Y":
            self.logger.error("Stream is Password-Protected")
            return
        elif channel.get("RESULT") == -6:
            self.logger.error("Login required")
            return
        elif channel.get("RESULT") != CHANNEL_RESULT_OK:
            return

        (broadcast, rmd, cdn) = (channel["BNO"], channel["RMD"], channel["CDN"])
        if not (broadcast and rmd and cdn):
            return

        for qkey in QUALITYS:
            hls_stream = self._get_hls_stream(broadcast, username, qkey, cdn, rmd)
            if hls_stream:
                yield qkey, hls_stream


__plugin__ = AfreecaTV
