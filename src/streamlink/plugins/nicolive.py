"""
$description Japanese live-streaming and video hosting social platform.
$url live.nicovideo.jp
$type live, vod
$account Required by some streams
$notes Timeshift is supported
"""

import logging
import re
from threading import Event
from urllib.parse import urljoin

from streamlink.plugin import Plugin, PluginError, pluginargument, pluginmatcher
from streamlink.plugin.api import useragents, validate
from streamlink.plugin.api.websocket import WebsocketClient
from streamlink.stream.hls import HLSStream, HLSStreamReader
from streamlink.utils.parse import parse_json
from streamlink.utils.times import hours_minutes_seconds
from streamlink.utils.url import update_qsd

log = logging.getLogger(__name__)


class NicoLiveWsClient(WebsocketClient):
    STREAM_OPENED_TIMEOUT = 6

    ready: Event
    opened: Event
    hls_stream_url: str

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.opened = Event()
        self.ready = Event()

    def on_open(self, wsapp):
        super().on_open(wsapp)
        self.send_playerversion()
        self.send_getpermit()

    def on_message(self, wsapp, data: str):
        log.debug(f"Received: {data}")
        message = parse_json(data)
        msgtype = message.get("type")
        msgdata = message.get("data", {})

        if msgtype == "ping":
            self.send_pong()

        elif msgtype == "stream" and msgdata.get("protocol") == "hls" and msgdata.get("uri"):
            self.hls_stream_url = msgdata.get("uri")
            self.ready.set()
            if self.opened.wait(self.STREAM_OPENED_TIMEOUT):
                log.debug("Stream opened, keeping websocket connection alive")
            else:
                log.info("Closing websocket connection")
                self.close()

        elif msgtype == "disconnect":
            reason = msgdata.get("reason", "Unknown reason")
            log.info(f"Received disconnect message: {reason}")
            self.close()

    def send_playerversion(self):
        self.send_json({
            "type": "startWatching",
            "data": {
                "stream": {
                    "quality": "abr",
                    "protocol": "hls",
                    "latency": "high",
                    "chasePlay": False
                },
                "room": {
                    "protocol": "webSocket",
                    "commentable": True
                },
                "reconnect": False
            }
        })

    def send_getpermit(self):
        self.send_json({
            "type": "getAkashic",
            "data": {
                "chasePlay": False
            }
        })

    def send_pong(self):
        self.send_json({"type": "pong"})
        self.send_json({"type": "keepSeat"})


class NicoLiveHLSStreamReader(HLSStreamReader):
    stream: "NicoLiveHLSStream"

    def open(self):
        self.stream.wsclient.opened.set()
        super().open()

    def close(self):
        super().close()
        self.stream.wsclient.close()


class NicoLiveHLSStream(HLSStream):
    __reader__ = NicoLiveHLSStreamReader
    wsclient: NicoLiveWsClient

    def set_wsclient(self, wsclient: NicoLiveWsClient):
        self.wsclient = wsclient


@pluginmatcher(re.compile(
    r"https?://(?P<domain>live\d*\.nicovideo\.jp)/watch/(lv|co)\d+"
))
@pluginargument(
    "email",
    sensitive=True,
    argument_name="niconico-email",
    metavar="EMAIL",
    help="The email or phone number associated with your Niconico account",
)
@pluginargument(
    "password",
    sensitive=True,
    argument_name="niconico-password",
    metavar="PASSWORD",
    help="The password of your Niconico account",
)
@pluginargument(
    "user-session",
    sensitive=True,
    argument_name="niconico-user-session",
    metavar="VALUE",
    help="""
        Value of the user-session token.

        Can be used as an alternative to providing a password.
    """,
)
@pluginargument(
    "purge-credentials",
    argument_name="niconico-purge-credentials",
    action="store_true",
    help="Purge cached Niconico credentials to initiate a new session and reauthenticate.",
)
@pluginargument(
    "timeshift-offset",
    type=hours_minutes_seconds,
    argument_name="niconico-timeshift-offset",
    metavar="[HH:]MM:SS",
    default=None,
    help="""
        Amount of time to skip from the beginning of a stream.

        Default is 00:00:00.
    """,
)
class NicoLive(Plugin):
    STREAM_READY_TIMEOUT = 6
    LOGIN_URL = "https://account.nicovideo.jp/login/redirector"
    LOGIN_URL_PARAMS = {
        "show_button_twitter": 1,
        "show_button_facebook": 1,
        "next_url": "/",
    }

    wsclient: NicoLiveWsClient

    def _get_streams(self):
        if self.get_option("purge_credentials"):
            self.clear_cookies()
            log.info("All credentials were successfully removed")

        self.session.http.headers.update({
            "User-Agent": useragents.CHROME,
        })

        self.niconico_web_login()

        wss_api_url = self.get_wss_api_url()
        if not wss_api_url:
            log.error(
                "Failed to get wss_api_url. "
                "Please check if the URL is correct, "
                "and make sure your account has access to the video."
            )
            return

        self.wsclient = NicoLiveWsClient(self.session, wss_api_url)
        self.wsclient.start()

        hls_stream_url = self._get_hls_stream_url()
        if not hls_stream_url:
            return

        offset = self.get_option("timeshift-offset")
        if offset and "timeshift" in wss_api_url:
            hls_stream_url = update_qsd(hls_stream_url, {"start": offset})

        for quality, stream in NicoLiveHLSStream.parse_variant_playlist(self.session, hls_stream_url).items():
            stream.set_wsclient(self.wsclient)
            yield quality, stream

    def _get_hls_stream_url(self):
        log.debug(f"Waiting for permit (for at most {self.STREAM_READY_TIMEOUT} seconds)...")
        if not self.wsclient.ready.wait(self.STREAM_READY_TIMEOUT) or not self.wsclient.is_alive():
            log.error("Waiting for permit timed out.")
            self.wsclient.close()
            return

        return self.wsclient.hls_stream_url

    def get_wss_api_url(self):
        try:
            data = self.session.http.get(self.url, schema=validate.Schema(
                validate.parse_html(),
                validate.xml_find(".//script[@id='embedded-data'][@data-props]"),
                validate.get("data-props"),
                validate.parse_json(),
                {"site": {
                    "relive": {
                        "webSocketUrl": validate.url(scheme="wss")
                    },
                    validate.optional("frontendId"): int
                }},
                validate.get("site"),
                validate.union_get(("relive", "webSocketUrl"), "frontendId")
            ))
        except PluginError:
            return

        wss_api_url, frontend_id = data
        if frontend_id is not None:
            wss_api_url = update_qsd(wss_api_url, {"frontend_id": frontend_id})

        return wss_api_url

    def niconico_web_login(self):
        user_session = self.get_option("user-session")
        email = self.get_option("email")
        password = self.get_option("password")

        if user_session is not None:
            log.info("Logging in via provided user session cookie")
            self.session.http.cookies.set(
                "user_session",
                user_session,
                path="/",
                domain="nicovideo.jp"
            )
            self.save_cookies()

        elif self.session.http.cookies.get("user_session"):
            log.info("Logging in via cached user session cookie")

        elif email is not None and password is not None:
            log.info("Logging in via provided email and password")
            root = self.session.http.post(
                self.LOGIN_URL,
                data={"mail_tel": email, "password": password},
                params=self.LOGIN_URL_PARAMS,
                schema=validate.Schema(validate.parse_html()),
            )

            if self.session.http.cookies.get("user_session"):
                log.info("Logged in.")
                self.save_cookies()
                return

            input_with_value = {}
            for elem in root.xpath(".//form[@action]//input"):
                if elem.attrib.get("value"):
                    input_with_value[elem.attrib.get("name")] = elem.attrib.get("value")
                elif elem.attrib.get("id") == "oneTimePw":
                    maxlength = int(elem.attrib.get("maxlength"))
                    oneTimePw = self.input_ask("Enter the 6 digit number included in email")
                    if len(oneTimePw) > maxlength:
                        log.error("invalid user input")
                        return
                    input_with_value[elem.attrib.get("name")] = oneTimePw
                else:
                    log.debug(f"unknown input: {elem.attrib.get('name')}")

            root = self.session.http.post(
                urljoin("https://account.nicovideo.jp", root.xpath("string(.//form[@action]/@action)")),
                data=input_with_value,
                schema=validate.Schema(validate.parse_html()),
            )
            log.debug(f"Cookies: {self.session.http.cookies.get_dict()}")
            if self.session.http.cookies.get("user_session") is None:
                error = root.xpath("string(//div[@class='formError']/div/text())")
                log.warning(f"Login failed: {error or 'unknown reason'}")
            else:
                log.info("Logged in.")
                self.save_cookies()


__plugin__ = NicoLive
