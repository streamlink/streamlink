"""
$description European live TV channels and video on-demand service. OTT service from Zattoo.
$url zattoo.com
$url iptv.glattvision.ch
$url www.saktv.ch
$url www.vtxtv.ch
$url mobiltv.quickline.com
$url www.quantum-tv.com
$url tvonline.ewe.de
$url nettv.netcologne.de
$url tvplus.m-net.de
$url player.waly.tv
$url www.1und1.tv
$url www.netplus.tv
$url www.bbv-tv.net
$url www.meinewelt.cc
$type live, vod
"""

import logging
import re
import uuid

from streamlink.cache import Cache
from streamlink.plugin import Plugin, pluginargument, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(
        r"""
            https?://
            (?P<base_url>
                (?:
                    iptv\.glattvision|www\.(?:saktv|vtxtv)
                )\.ch
                |(?:
                    mobiltv\.quickline|www\.quantum-tv|zattoo
                )\.com
                |(?:
                    tvonline\.ewe|nettv\.netcologne|tvplus\.m-net
                )\.de
                |(?:
                    player\.waly|www\.(?:1und1|netplus)
                )\.tv
                |www\.bbv-tv\.net
                |www\.meinewelt\.cc
            )/
            (?:
                (?:
                    recording(?:s\?recording=|/)
                    |
                    (?:ondemand/)?watch/[^/\s]+/[^/]+/
                )(?P<recording_id>\d+)
                |
                (?:
                    (?:live/|watch/)|(?:channels(?:/\w+)?|guide)\?channel=
                )(?P<channel>[^/\s]+)
                |
                ondemand(?:\?video=|/watch/)(?P<vod_id>[^-]+)
            )
        """,
        re.VERBOSE,
    ),
)
@pluginargument(
    "email",
    requires=["password"],
    metavar="EMAIL",
    help="The email associated with your zattoo account, required to access any zattoo stream.",
)
@pluginargument(
    "password",
    sensitive=True,
    metavar="PASSWORD",
    help="A zattoo account password to use with --zattoo-email.",
)
@pluginargument(
    "purge-credentials",
    action="store_true",
    help="Purge cached zattoo credentials to initiate a new session and reauthenticate.",
)
@pluginargument(
    "stream-types",
    metavar="TYPES",
    type="comma_list_filter",
    type_kwargs={"acceptable": ["dash", "hls7"]},
    default=["dash"],
    help="""
        A comma-delimited list of stream types which should be used.

        The following types are allowed: dash, hls7

        Default is "dash".
    """,
)
class Zattoo(Plugin):
    TIME_CONTROL = 60 * 60 * 2
    TIME_SESSION = 60 * 60 * 24 * 30

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.domain = self.match.group("base_url")
        self._session_attributes = Cache(
            filename="plugin-cache.json",
            key_prefix=f"zattoo:attributes:{self.domain}",
        )
        self._uuid = self._session_attributes.get("uuid")
        self._authed = (
            self._session_attributes.get("power_guide_hash")
            and self._uuid
            and self.session.http.cookies.get("pzuid", domain=self.domain)
            and self.session.http.cookies.get("beaker.session.id", domain=self.domain)
        )
        self._session_control = self._session_attributes.get("session_control", False)
        self.base_url = "https://{0}".format(self.domain)
        self.headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": self.base_url,
        }

    def _hello(self):
        log.debug("_hello ...")
        app_token = self.session.http.get(
            f"{self.base_url}/token.json",
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "success": bool,
                    "session_token": str,
                },
                validate.get("session_token"),
            ),
        )
        if self._uuid:
            uuid_data = self._uuid
        else:
            uuid_data = str(uuid.uuid4())
            self._session_attributes.set("uuid", uuid_data, expires=self.TIME_SESSION)

        params = {
            "app_version": "3.2120.1",
            "client_app_token": app_token,
            "format": "json",
            "lang": "en",
            "uuid": uuid_data,
        }
        res = self.session.http.post(
            f"{self.base_url}/zapi/v3/session/hello",
            headers=self.headers,
            data=params,
            schema=validate.Schema(
                validate.parse_json(),
                validate.any({"active": bool}, {"success": bool}),
            ),
        )
        if res.get("active") or res.get("success"):
            log.debug("Hello was successful.")
        else:
            log.debug("Hello failed.")

    def _login(self, email, password):
        log.debug("_login ...")
        data = self.session.http.post(
            f"{self.base_url}/zapi/v3/account/login",
            headers=self.headers,
            data={
                "login": email,
                "password": password,
                "remember": "true",
                "format": "json",
            },
            acceptable_status=(200, 400),
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    {"active": bool, "power_guide_hash": str},
                    {"success": bool},
                ),
            ),
        )

        if data.get("active"):
            log.debug("Login was successful.")
        else:
            log.debug("Login failed.")
            return

        self._authed = data["active"]
        self.save_cookies(default_expires=self.TIME_SESSION)
        self._session_attributes.set("power_guide_hash", data["power_guide_hash"], expires=self.TIME_SESSION)
        self._session_attributes.set("session_control", True, expires=self.TIME_CONTROL)

    def _watch(self):
        log.debug("_watch ...")
        channel = self.match.group("channel")
        vod_id = self.match.group("vod_id")
        recording_id = self.match.group("recording_id")

        params = {"https_watch_urls": True}
        if channel:
            watch_url = f"{self.base_url}/zapi/watch"
            params_cid = self._get_params_cid(channel)
            if not params_cid:
                return
            params.update(params_cid)
        elif vod_id:
            log.debug("Found vod_id: {0}".format(vod_id))
            watch_url = f"{self.base_url}/zapi/avod/videos/{vod_id}/watch"
        elif recording_id:
            log.debug("Found recording_id: {0}".format(recording_id))
            watch_url = f"{self.base_url}/zapi/watch/recording/{recording_id}"
        else:
            log.debug("Missing watch_url")
            return

        zattoo_stream_types = self.get_option("stream-types")
        for stream_type in zattoo_stream_types:
            params_stream_type = {"stream_type": stream_type}
            params.update(params_stream_type)

            data = self.session.http.post(
                watch_url,
                headers=self.headers,
                data=params,
                acceptable_status=(200, 402, 403, 404),
                schema=validate.Schema(
                    validate.parse_json(),
                    validate.any(
                        {
                            "success": validate.transform(bool),
                            "stream": {
                                "watch_urls": [
                                    {
                                        "url": validate.url(),
                                        validate.optional("maxrate"): int,
                                        validate.optional("audio_channel"): str,
                                    },
                                ],
                                validate.optional("quality"): str,
                            },
                        },
                        {
                            "success": validate.transform(bool),
                            "internal_code": int,
                            validate.optional("http_status"): int,
                        },
                    ),
                ),
            )

            if not data["success"]:
                if data["internal_code"] == 401:
                    log.error(f"invalid stream_type {stream_type}")
                elif data["internal_code"] == 421:
                    log.error("Unfortunately streaming is not permitted in this country or this channel does not exist.")
                elif data["internal_code"] == 422:
                    log.error("Paid subscription required for this channel.")
                    log.info("If paid subscription exist, use --zattoo-purge-credentials to start a new session.")
                else:
                    log.debug(f"unknown error {data!r}")
                    log.debug("Force session reset for watch_url")
                    self.reset_session()
                continue

            log.debug(f"Found data for {stream_type}")
            if stream_type == "hls7":
                for url in data["stream"]["watch_urls"]:
                    yield from HLSStream.parse_variant_playlist(
                        self.session,
                        url["url"],
                        ffmpeg_options={"copyts": True},
                    ).items()
            elif stream_type == "dash":
                for url in data["stream"]["watch_urls"]:
                    yield from DASHStream.parse_manifest(self.session, url["url"]).items()

    def _get_params_cid(self, channel):
        log.debug("get channel ID for {0}".format(channel))
        try:
            res = self.session.http.get(
                f"{self.base_url}/zapi/v2/cached/channels/{self._session_attributes.get('power_guide_hash')}",
                headers=self.headers,
                params={"details": "False"},
            )
        except Exception:
            log.debug("Force session reset for _get_params_cid")
            self.reset_session()
            return False

        data = self.session.http.json(
            res,
            schema=validate.Schema(
                {
                    "success": validate.transform(bool),
                    "channel_groups": [
                        {
                            "channels": [
                                {
                                    "display_alias": str,
                                    "cid": str,
                                    "qualities": [
                                        {
                                            "title": str,
                                            "stream_types": validate.all(
                                                [str],
                                                validate.filter(
                                                    lambda n: not re.match(r"(.+_(?:fairplay|playready|widevine))", n),
                                                ),
                                            ),
                                            "level": str,
                                            "availability": str,
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
                validate.get("channel_groups"),
            ),
        )

        c_list = [channel for channel_group in data for channel in channel_group["channels"]]
        cid = None
        zattoo_list = []
        for c in c_list:
            zattoo_list.append(c["display_alias"])
            if c["display_alias"] == channel:
                cid = c["cid"]
                log.debug(f"{c!r}")

        log.trace(f"Available zattoo channels in this country: {', '.join(sorted(zattoo_list))}")

        if not cid:
            cid = channel

        log.debug("CHANNEL ID: {0}".format(cid))
        return {"cid": cid}

    def reset_session(self):
        self._session_attributes.set("power_guide_hash", None, expires=0)
        self._session_attributes.set("uuid", None, expires=0)
        self.clear_cookies()
        self._authed = False

    def _get_streams(self):
        email = self.get_option("email")
        password = self.get_option("password")

        if self.options.get("purge_credentials"):
            self.reset_session()
            log.info("All credentials were successfully removed.")
        elif self._authed and not self._session_control:
            # check every two hours, if the session is actually valid
            log.debug("Session control for {0}".format(self.domain))
            active = self.session.http.get(
                f"{self.base_url}/zapi/v3/session",
                schema=validate.Schema(validate.parse_json(), {"active": bool}, validate.get("active")),
            )
            if active:
                self._session_attributes.set("session_control", True, expires=self.TIME_CONTROL)
                log.debug("User is logged in")
            else:
                log.debug("User is not logged in")
                self._authed = False

        if not self._authed and (not email and not password):
            log.error("A login for Zattoo is required, use --zattoo-email EMAIL --zattoo-password PASSWORD to set them")
            return

        if not self._authed:
            self._hello()
            self._login(email, password)

        if self._authed:
            return self._watch()


__plugin__ = Zattoo
