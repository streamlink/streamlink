"""
$description TV and live video game broadcasts, artist performances and personal daily-life video blogs & shows.
$url play.afreecatv.com
$type live
"""

import logging
import re

from streamlink.plugin import Plugin, pluginargument, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream, HLSStreamReader, HLSStreamWriter


log = logging.getLogger(__name__)


class AfreecaHLSStreamWriter(HLSStreamWriter):
    def should_filter_sequence(self, sequence):
        return "preloading" in sequence.segment.uri or super().should_filter_sequence(sequence)


class AfreecaHLSStreamReader(HLSStreamReader):
    __writer__ = AfreecaHLSStreamWriter


class AfreecaHLSStream(HLSStream):
    __reader__ = AfreecaHLSStreamReader


@pluginmatcher(re.compile(
    r"https?://play\.afreecatv\.com/(?P<username>\w+)(?:/(?P<bno>:\d+))?",
))
@pluginargument(
    "username",
    sensitive=True,
    requires=["password"],
    metavar="USERNAME",
    help="The username used to register with afreecatv.com.",
)
@pluginargument(
    "password",
    sensitive=True,
    metavar="PASSWORD",
    help="A afreecatv.com account password to use with --afreeca-username.",
)
@pluginargument(
    "purge-credentials",
    action="store_true",
    help="Purge cached AfreecaTV credentials to initiate a new session and reauthenticate.",
)
class AfreecaTV(Plugin):
    _re_bno = re.compile(r"var nBroadNo = (?P<bno>\d+);")

    CHANNEL_API_URL = "http://live.afreecatv.com/afreeca/player_live_api.php"
    CHANNEL_RESULT_OK = 1
    QUALITYS = ["original", "hd", "sd"]
    QUALITY_WEIGHTS = {
        "original": 1080,
        "hd": 720,
        "sd": 480,
    }

    _schema_channel = validate.Schema(
        {
            "CHANNEL": {
                "RESULT": validate.transform(int),
                validate.optional("BPWD"): str,
                validate.optional("BNO"): str,
                validate.optional("RMD"): str,
                validate.optional("AID"): str,
                validate.optional("CDN"): str,
            },
        },
        validate.get("CHANNEL"),
    )
    _schema_stream = validate.Schema(
        {
            validate.optional("view_url"): validate.url(
                scheme=validate.any("rtmp", "http"),
            ),
            "stream_status": str,
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._authed = (
            self.session.http.cookies.get("PdboxBbs")
            and self.session.http.cookies.get("PdboxSaveTicket")
            and self.session.http.cookies.get("PdboxTicket")
            and self.session.http.cookies.get("PdboxUser")
            and self.session.http.cookies.get("RDB")
        )

    @classmethod
    def stream_weight(cls, key):
        weight = cls.QUALITY_WEIGHTS.get(key)
        if weight:
            return weight, "afreeca"

        return Plugin.stream_weight(key)

    def _get_channel_info(self, broadcast, username):
        data = {
            "bid": username,
            "bno": broadcast,
            "from_api": "0",
            "mode": "landing",
            "player_type": "html5",
            "pwd": "",
            "stream_type": "common",
            "type": "live",
        }
        res = self.session.http.post(self.CHANNEL_API_URL, data=data)
        return self.session.http.json(res, schema=self._schema_channel)

    def _get_hls_key(self, broadcast, username, quality):
        data = {
            "bid": username,
            "bno": broadcast,
            "from_api": "0",
            "mode": "landing",
            "player_type": "html5",
            "pwd": "",
            "quality": quality,
            "stream_type": "common",
            "type": "aid",
        }
        res = self.session.http.post(self.CHANNEL_API_URL, data=data)
        return self.session.http.json(res, schema=self._schema_channel)

    def _get_stream_info(self, broadcast, quality, rmd):
        params = {
            "return_type": "gs_cdn_pc_web",
            "broad_key": f"{broadcast}-common-{quality}-hls",
        }
        res = self.session.http.get(f"{rmd}/broad_stream_assign.html", params=params)
        return self.session.http.json(res, schema=self._schema_stream)

    def _get_hls_stream(self, broadcast, username, quality, rmd):
        keyjson = self._get_hls_key(broadcast, username, quality)

        if keyjson["RESULT"] != self.CHANNEL_RESULT_OK:
            return
        key = keyjson["AID"]

        info = self._get_stream_info(broadcast, quality, rmd)

        if "view_url" in info:
            return AfreecaHLSStream(self.session, info["view_url"], params={"aid": key})

    def _login(self, username, password):
        data = {
            "szWork": "login",
            "szType": "json",
            "szUid": username,
            "szPassword": password,
            "isSaveId": "true",
            "isSavePw": "false",
            "isSaveJoin": "false",
            "isLoginRetain": "Y",
        }
        res = self.session.http.post("https://login.afreecatv.com/app/LoginAction.php", data=data)
        data = self.session.http.json(res)
        log.trace(f"{data!r}")
        if data["RESULT"] != self.CHANNEL_RESULT_OK:
            return False
        self.save_cookies()
        return True

    def _get_streams(self):
        login_username = self.get_option("username")
        login_password = self.get_option("password")

        self.session.http.headers.update({"Referer": self.url, "Origin": "http://play.afreecatv.com"})

        if self.options.get("purge_credentials"):
            self.clear_cookies()
            self._authed = False
            log.info("All credentials were successfully removed")

        if self._authed:
            log.debug("Attempting to authenticate using cached cookies")
        elif login_username and login_password:
            log.debug("Attempting to login using username and password")
            if self._login(login_username, login_password):
                log.info("Login was successful")
            else:
                log.error("Failed to login")

        m = self.match.groupdict()
        username = m["username"]
        bno = m["bno"]
        if bno is None:
            res = self.session.http.get(self.url)
            m = self._re_bno.search(res.text)
            if not m:
                log.error("Could not find broadcast number.")
                return
            bno = m.group("bno")

        channel = self._get_channel_info(bno, username)
        log.trace(f"{channel!r}")
        if channel.get("BPWD") == "Y":
            log.error("Stream is Password-Protected")
            return
        elif channel.get("RESULT") == -6:
            log.error("Login required")
            return
        elif channel.get("RESULT") != self.CHANNEL_RESULT_OK:
            return

        (broadcast, rmd) = (channel["BNO"], channel["RMD"])
        if not (broadcast and rmd):
            return

        for qkey in self.QUALITYS:
            hls_stream = self._get_hls_stream(broadcast, username, qkey, rmd)
            if hls_stream:
                yield qkey, hls_stream


__plugin__ = AfreecaTV
