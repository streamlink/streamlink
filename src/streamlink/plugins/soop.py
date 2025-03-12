"""
$description TV and live video game broadcasts, artist performances and personal daily-life video blogs & shows.
$url play.sooplive.co.kr
$url play.afreecatv.com
$type live
$metadata id
$metadata author
$metadata title
"""

from __future__ import annotations

import argparse
import logging
import re

from streamlink.exceptions import NoStreamsError
from streamlink.plugin import Plugin, pluginargument, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream, HLSStreamReader, HLSStreamWriter


log = logging.getLogger(__name__)


class SoopHLSStreamWriter(HLSStreamWriter):
    def should_filter_segment(self, segment):
        return "preloading" in segment.uri or super().should_filter_segment(segment)


class SoopHLSStreamReader(HLSStreamReader):
    __writer__ = SoopHLSStreamWriter


class SoopHLSStream(HLSStream):
    __reader__ = SoopHLSStreamReader


@pluginmatcher(
    re.compile(r"https?://play\.(sooplive\.co\.kr|afreecatv\.com)/(?P<channel>\w+)(?:/(?P<bno>\d+))?"),
)
@pluginargument(
    "username",
    sensitive=True,
    requires=["password"],
    metavar="USERNAME",
    help="The username used to register with sooplive.co.kr.",
)
@pluginargument(
    "password",
    sensitive=True,
    metavar="PASSWORD",
    help="A sooplive.co.kr account password to use with --soop-username.",
)
@pluginargument(
    "purge-credentials",
    action="store_true",
    help="Purge cached Soop credentials to initiate a new session and reauthenticate.",
)
@pluginargument(
    "stream-password",
    metavar="STREAM_PASSWORD",
    help="The password for the stream.",
)
@pluginargument(
    "afreeca-username",
    argument_name="afreeca-username",
    sensitive=True,
    help=argparse.SUPPRESS,
)
@pluginargument(
    "afreeca-password",
    argument_name="afreeca-password",
    sensitive=True,
    help=argparse.SUPPRESS,
)
@pluginargument(
    "afreeca-purge-credentials",
    argument_name="afreeca-purge-credentials",
    action="store_true",
    help=argparse.SUPPRESS,
)
@pluginargument(
    "afreeca-stream-password",
    argument_name="afreeca-stream-password",
    help=argparse.SUPPRESS,
)
class Soop(Plugin):
    _OPTIONS_DEPRECATED = {
        "afreeca-username": "username",
        "afreeca-password": "password",
        "afreeca-purge-credentials": "purge-credentials",
        "afreeca-stream-password": "stream-password",
    }

    CDN_TYPE_MAPPING = {
        "gs_cdn": "gs_cdn_pc_web",
    }

    CHANNEL_RESULT_OK = 1
    CHANNEL_LOGIN_REQUIRED = -6

    CHANNEL_API_URL = "https://live.sooplive.co.kr/afreeca/player_live_api.php"
    CHANNEL_API_DATA_COMMON = {
        "from_api": "0",
        "mode": "landing",
        "player_type": "html5",
        "stream_type": "common",
    }

    STREAM_PASSWORD_PROTECTED = "Y"

    AUTH_CHECK_URL = "https://afevent2.sooplive.co.kr/api/get_private_info.php"

    LOGIN_URL = "https://login.sooplive.co.kr/app/LoginAction.php"
    LOGIN_RESULT_OK = 1

    _schema_channel = validate.Schema(
        validate.parse_json(),
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
                validate.optional("VIEWPRESET"): [
                    {
                        "label": str,
                        "name": str,
                    },
                ],
            },
        },
        validate.get("CHANNEL"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for opt_deprecated, opt_name in self._OPTIONS_DEPRECATED.items():
            if (opt_value := self.options.get(opt_deprecated)) and not self.options.get(opt_name):
                self.options.set(opt_name, opt_value)

        if self.options.get("purge_credentials"):
            self.clear_cookies()
            log.info("All credentials were successfully removed")

    def _get_channel_info(self, channel, broadcast) -> tuple[int, str, str, str, str, str, str, list[dict[str, str]]]:
        return self.session.http.post(
            self.CHANNEL_API_URL,
            data={
                **self.CHANNEL_API_DATA_COMMON,
                "type": "live",
                "bid": channel,
                "bno": broadcast,
                "pwd": "",
            },
            schema=validate.Schema(
                self._schema_channel,
                validate.union_get(
                    "RESULT",
                    "BNO",
                    "BJNICK",
                    "TITLE",
                    "RMD",
                    "CDN",
                    "BPWD",
                    "VIEWPRESET",
                ),
            ),
        )

    def _get_hls_key(self, channel, broadcast, quality, pwd) -> tuple[int, str]:
        return self.session.http.post(
            self.CHANNEL_API_URL,
            data={
                **self.CHANNEL_API_DATA_COMMON,
                "type": "aid",
                "bid": channel,
                "bno": broadcast,
                "pwd": pwd or "",
                "quality": quality,
            },
            schema=validate.Schema(
                self._schema_channel,
                validate.union_get("RESULT", "AID"),
            ),
        )

    def _get_stream_info(self, rmd, cdn, broadcast, quality) -> str | None:
        return self.session.http.get(
            f"{rmd}/broad_stream_assign.html",
            params={
                "return_type": next((v for k, v in self.CDN_TYPE_MAPPING.items() if k in cdn), cdn),
                "broad_key": f"{broadcast}-common-{quality}-hls",
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    validate.optional("view_url"): validate.url(),
                    "stream_status": str,
                },
                validate.get("view_url"),
            ),
        )

    def _get_hls_stream(self, rmd, cdn, channel, broadcast, quality, pwd):
        result, aid = self._get_hls_key(channel, broadcast, quality, pwd)
        if result != self.CHANNEL_RESULT_OK:
            return

        view_url = self._get_stream_info(rmd, cdn, broadcast, quality)
        if not view_url:
            return

        return SoopHLSStream(self.session, view_url, params={"aid": aid})

    def _get_bno(self):
        bno = self.session.http.get(
            self.url,
            schema=validate.Schema(
                re.compile(r"window\.nBroadNo\s*=\s*(?P<bno>\d+);"),
                validate.none_or_all(validate.get("bno")),
            ),
        )
        if not bno:
            raise NoStreamsError("Could not find broadcast number")

        return bno

    def _check_auth(self):
        return self.session.http.get(
            self.AUTH_CHECK_URL,
            schema=validate.Schema(
                validate.parse_json(),
                {"CHANNEL": {"LOGIN_ID": str}},
                validate.get(("CHANNEL", "LOGIN_ID")),
                validate.transform(lambda login_id: len(login_id) > 0),
            ),
        )

    def _login(self, username, password):
        result = self.session.http.post(
            self.LOGIN_URL,
            data={
                "szWork": "login",
                "szType": "json",
                "szUid": username,
                "szPassword": password,
                "isSaveId": "true",
                "isSavePw": "false",
                "isSaveJoin": "false",
                "isLoginRetain": "Y",
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "RESULT": validate.transform(int),
                },
                validate.get("RESULT"),
            ),
        )

        if result != self.LOGIN_RESULT_OK:
            return False

        self.save_cookies()
        return True

    def _get_streams(self):
        login_username = self.get_option("username")
        login_password = self.get_option("password")
        stream_password = self.get_option("stream-password")

        self.session.http.headers.update({
            "Referer": self.url,
            "Origin": "https://play.sooplive.co.kr",
        })

        authed = False
        if self.session.http.cookies.get_dict(domain=".sooplive.co.kr"):
            if authed := self._check_auth():
                log.debug("Authentication using stored credentials was successful")
            else:
                log.error("Authentication using stored credentials has failed. Please re-authenticate or purge credentials.")

        if not authed and login_username and login_password:
            log.debug("Attempting to login using username and password")
            if self._login(login_username, login_password):
                log.info("Login was successful")
            else:
                log.error("Login has failed")

        channel = self.match["channel"]
        bno = self.match["bno"] or self._get_bno()

        result, self.id, self.author, self.title, rmd, cdn, bpwd, viewpreset = self._get_channel_info(channel, bno)
        if result == self.CHANNEL_LOGIN_REQUIRED:
            log.error("Login required")
            return
        if result != self.CHANNEL_RESULT_OK:
            return

        if not self.id or not rmd:
            return

        streams = {}
        for item in viewpreset:
            if item["name"] == "auto":
                continue
            if hls_stream := self._get_hls_stream(
                rmd=rmd,
                cdn=cdn,
                channel=channel,
                broadcast=self.id,
                quality=item["name"],
                pwd=stream_password,
            ):
                streams[item["label"]] = hls_stream

        if not streams and bpwd == self.STREAM_PASSWORD_PROTECTED:
            log.error("Stream is password protected")
            return

        return streams


__plugin__ = Soop
