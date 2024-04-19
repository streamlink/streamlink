"""
$description TV and live video game broadcasts, artist performances and personal daily-life video blogs & shows.
$url play.afreecatv.com
$type live
$metadata id
$metadata author
$metadata title
"""

import logging
import re

from streamlink.plugin import Plugin, pluginargument, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream, HLSStreamReader, HLSStreamWriter


log = logging.getLogger(__name__)


class AfreecaHLSStreamWriter(HLSStreamWriter):
    def should_filter_segment(self, segment):
        return "preloading" in segment.uri or super().should_filter_segment(segment)


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
@pluginargument(
    "stream-password",
    metavar="STREAM_PASSWORD",
    help="The password for the stream.",
)
class AfreecaTV(Plugin):
    _re_bno = re.compile(r"window\.nBroadNo\s*=\s*(?P<bno>\d+);")

    CHANNEL_API_URL = "https://live.afreecatv.com/afreeca/player_live_api.php"
    CHANNEL_RESULT_OK = 1
    CHANNEL_LOGIN_REQUIRED = -6

    _schema_channel = validate.Schema(
        {
            "CHANNEL": {
                "RESULT": validate.transform(int),
                validate.optional("BPWD"): validate.any(str, None),
                validate.optional("BNO"): validate.any(str, None),
                validate.optional("RMD"): validate.any(str, None),
                validate.optional("AID"): validate.any(str, None),
                validate.optional("CDN"): validate.any(str, None),
                validate.optional("BJNICK"): validate.any(str, None),
                validate.optional("TITLE"): validate.any(str, None),
                validate.optional("VIEWPRESET"): [{
                    "label": str,
                    "name": str,
                }],
            },
        },
        validate.get("CHANNEL"),
    )
    _schema_stream = validate.Schema(
        {
            validate.optional("view_url"): validate.url(
                scheme=validate.any("rtmp", "https"),
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

    def _get_hls_key(self, broadcast, username, quality, stream_password):
        data = {
            "bid": username,
            "bno": broadcast,
            "from_api": "0",
            "mode": "landing",
            "player_type": "html5",
            "pwd": stream_password or "",
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

    def _get_hls_stream(self, broadcast, username, quality, rmd, stream_password):
        keyjson = self._get_hls_key(broadcast, username, quality, stream_password)

        if keyjson.get("RESULT") != self.CHANNEL_RESULT_OK:
            return
        key = keyjson.get("AID")

        info = self._get_stream_info(broadcast, quality, rmd)

        if "view_url" in info:
            return AfreecaHLSStream(self.session, info.get("view_url"), params={"aid": key})

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
        if data.get("RESULT") != self.CHANNEL_RESULT_OK:
            return False
        self.save_cookies()
        return True

    def _get_streams(self):
        login_username = self.get_option("username")
        login_password = self.get_option("password")
        stream_password = self.get_option("stream-password")

        self.session.http.headers.update({"Referer": self.url, "Origin": "https://play.afreecatv.com"})

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
        username = m.get("username")
        bno = m.get("bno")
        if bno is None:
            res = self.session.http.get(self.url)
            m = self._re_bno.search(res.text)
            if not m:
                log.error("Could not find broadcast number.")
                return
            bno = m.group("bno")

        channel = self._get_channel_info(bno, username)
        log.trace(f"{channel!r}")
        if channel.get("RESULT") == self.CHANNEL_LOGIN_REQUIRED:
            log.error("Login required")
            return
        if channel.get("RESULT") != self.CHANNEL_RESULT_OK:
            return

        (broadcast, rmd) = (channel.get("BNO"), channel.get("RMD"))
        if not (broadcast and rmd):
            return

        self.id = channel.get("BNO")
        self.author = channel.get("BJNICK")
        self.title = channel.get("TITLE")

        streams = {}
        for item in channel.get("VIEWPRESET"):
            if item["name"] == "auto":
                continue
            if hls_stream := self._get_hls_stream(broadcast, username, item["name"], rmd, stream_password):
                streams[item["label"]] = hls_stream

        if not streams and channel.get("BPWD") == "Y":
            log.error("Stream is password protected")
            return

        return streams


__plugin__ = AfreecaTV
