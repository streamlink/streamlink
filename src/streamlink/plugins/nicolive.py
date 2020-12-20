import json
import logging
import re
import threading
import time
from urllib.parse import unquote_plus, urlparse

import websocket

from streamlink.plugin import Plugin, PluginArgument, PluginArguments
from streamlink.plugin.api import useragents
from streamlink.stream import HLSStream
from streamlink.utils.times import hours_minutes_seconds
from streamlink.utils.url import update_qsd

_log = logging.getLogger(__name__)

_url_re = re.compile(
    r"^https?://(?P<domain>live[0-9]*\.nicovideo\.jp)/watch/lv[0-9]*")

_login_url = "https://account.nicovideo.jp/login/redirector"

_login_url_params = {
    "show_button_twitter": 1,
    "show_button_facebook": 1,
    "next_url": "/"}


class NicoLive(Plugin):
    arguments = PluginArguments(
        PluginArgument(
            "email",
            argument_name="niconico-email",
            sensitive=True,
            metavar="EMAIL",
            help="The email or phone number associated with your "
                 "Niconico account"),
        PluginArgument(
            "password",
            argument_name="niconico-password",
            sensitive=True,
            metavar="PASSWORD",
            help="The password of your Niconico account"),
        PluginArgument(
            "user-session",
            argument_name="niconico-user-session",
            sensitive=True,
            metavar="VALUE",
            help="Value of the user-session token \n(can be used in "
                 "case you do not want to put your password here)"),
        PluginArgument(
            "timeshift-offset",
            type=hours_minutes_seconds,
            argument_name="niconico-timeshift-offset",
            metavar="[HH:]MM:SS",
            default=None,
            help="Amount of time to skip from the beginning of a stream. "
                 "Default is 00:00:00."))

    is_stream_ready = False
    is_stream_ended = False
    watching_interval = 30
    watching_interval_worker_thread = None
    stream_reader = None
    _ws = None

    frontend_id = None

    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url) is not None

    def _get_streams(self):
        self.url = self.url.split("?")[0]
        self.session.http.headers.update({
            "User-Agent": useragents.CHROME,
        })

        if not self.get_wss_api_url():
            _log.debug("Coundn't extract wss_api_url. Attempting login...")
            if not self.niconico_web_login():
                return None
            if not self.get_wss_api_url():
                _log.error("Failed to get wss_api_url.")
                _log.error(
                    "Please check if the URL is correct, "
                    "and make sure your account has access to the video.")
                return None

        self.api_connect(self.wss_api_url)

        i = 0
        while not self.is_stream_ready:
            if i % 10 == 0:
                _log.debug("Waiting for permit...")
            if i == 600:
                _log.error("Waiting for permit timed out.")
                return None
            if self.is_stream_ended:
                return None
            time.sleep(0.1)
            i += 1

        streams = HLSStream.parse_variant_playlist(
            self.session, self.hls_stream_url)

        nico_streams = {}
        for s in streams:
            nico_stream = NicoHLSStream(streams[s], self)
            nico_streams[s] = nico_stream

        return nico_streams

    def get_wss_api_url(self):
        _log.debug("Getting video page: {0}".format(self.url))
        resp = self.session.http.get(self.url)

        try:
            self.wss_api_url = extract_text(
                resp.text, "&quot;webSocketUrl&quot;:&quot;", "&quot;")
            if not self.wss_api_url:
                return False
        except Exception as e:
            _log.debug(e)
            _log.debug("Failed to extract wss api url")
            return False

        try:
            self.frontend_id = extract_text(
                resp.text, "&quot;frontendId&quot;:", ",&quot;")
        except Exception as e:
            _log.debug(e)
            _log.warning("Failed to extract frontend id")

        self.wss_api_url = "{0}&frontend_id={1}".format(self.wss_api_url, self.frontend_id)

        _log.debug("Video page response code: {0}".format(resp.status_code))
        _log.trace("Video page response body: {0}".format(resp.text))
        _log.debug("Got wss_api_url: {0}".format(self.wss_api_url))
        _log.debug("Got frontend_id: {0}".format(self.frontend_id))

        return self.wss_api_url.startswith("wss://")

    def api_on_open(self):
        self.send_playerversion()
        require_new_stream = not self.is_stream_ready
        self.send_getpermit(require_new_stream=require_new_stream)

    def api_on_error(self, ws, error=None):
        if error:
            _log.warning(error)
        _log.warning("wss api disconnected.")
        _log.warning("Attempting to reconnect in 5 secs...")
        time.sleep(5)
        self.api_connect(self.wss_api_url)

    def api_connect(self, url):
        # Proxy support adapted from the UStreamTV plugin (ustreamtv.py)
        proxy_url = self.session.get_option("https-proxy")
        if proxy_url is None:
            proxy_url = self.session.get_option("http-proxy")
        proxy_options = parse_proxy_url(proxy_url)
        if proxy_options.get('http_proxy_host'):
            _log.debug("Using proxy ({0}://{1}:{2})".format(
                proxy_options.get('proxy_type') or "http",
                proxy_options.get('http_proxy_host'),
                proxy_options.get('http_proxy_port') or 80))

        _log.debug("Connecting: {0}".format(url))
        self._ws = websocket.WebSocketApp(
            url,
            header=["User-Agent: {0}".format(useragents.CHROME)],
            on_open=self.api_on_open,
            on_message=self.handle_api_message,
            on_error=self.api_on_error)
        self.ws_worker_thread = threading.Thread(
            target=self._ws.run_forever,
            args=proxy_options)
        self.ws_worker_thread.daemon = True
        self.ws_worker_thread.start()

    def send_message(self, type_, body):
        msg = {"type": type_, "body": body}
        msg_json = json.dumps(msg)
        _log.debug(f"Sending: {msg_json}")
        if self._ws and self._ws.sock.connected:
            self._ws.send(msg_json)
        else:
            _log.warning("wss api is not connected.")

    def send_no_body_message(self, type_):
        msg = {"type": type_}
        msg_json = json.dumps(msg)
        _log.debug(f"Sending: {msg_json}")
        if self._ws and self._ws.sock.connected:
            self._ws.send(msg_json)
        else:
            _log.warning("wss api is not connected.")

    def send_custom_message(self, msg):
        msg_json = json.dumps(msg)
        _log.debug(f"Sending: {msg_json}")
        if self._ws and self._ws.sock.connected:
            self._ws.send(msg_json)
        else:
            _log.warning("wss api is not connected.")

    def send_playerversion(self):
        body = {
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
        }
        self.send_custom_message(body)

    def send_getpermit(self, require_new_stream=True):
        body = {
            "type": "getAkashic",
            "data": {
                "chasePlay": False
            }
        }
        self.send_custom_message(body)

    def send_watching(self):
        body = {
            "command": "watching",
            "params": [self.broadcast_id, "-1", "0"]
        }
        self.send_message("watch", body)

    def send_pong(self):
        self.send_no_body_message("pong")
        self.send_no_body_message("keepSeat")

    def handle_api_message(self, message):
        _log.debug(f"Received: {message}")
        message_parsed = json.loads(message)

        if message_parsed["type"] == "stream":
            data = message_parsed["data"]
            self.hls_stream_url = data["uri"]
            # load in the offset for timeshift live videos
            offset = self.get_option("timeshift-offset")
            if offset and 'timeshift' in self.wss_api_url:
                self.hls_stream_url = update_qsd(self.hls_stream_url, {"start": offset})
            self.is_stream_ready = True

        if message_parsed["type"] == "watch":
            body = message_parsed["body"]
            command = body["command"]

            if command == "currentstream":
                current_stream = body["currentStream"]
                self.hls_stream_url = current_stream["uri"]
                self.is_stream_ready = True

            elif command == "watchinginterval":
                self.watching_interval = int(body["params"][0])
                _log.debug("Got watching_interval: {0}".format(
                    self.watching_interval))

                if self.watching_interval_worker_thread is None:
                    _log.debug("send_watching_scheduler starting.")
                    self.watching_interval_worker_thread = threading.Thread(
                        target=self.send_watching_scheduler)
                    self.watching_interval_worker_thread.daemon = True
                    self.watching_interval_worker_thread.start()

                else:
                    _log.debug("send_watching_scheduler already running.")

            elif command == "disconnect":
                _log.info("Websocket API closed.")
                _log.info("Stream ended.")
                self.is_stream_ended = True

                if self.stream_reader is not None:
                    self.stream_reader.close()
                    _log.info("Stream reader closed.")

        elif message_parsed["type"] == "ping":
            self.send_pong()

    def send_watching_scheduler(self):
        """
        Periodically send "watching" command to the API.
        This is necessary to keep the session alive.
        """
        while not self.is_stream_ended:
            self.send_watching()
            time.sleep(self.watching_interval)

    def niconico_web_login(self):
        user_session = self.get_option("user-session")
        email = self.get_option("email")
        password = self.get_option("password")

        if user_session is not None:
            _log.info("User session cookie is provided. Using it.")
            self.session.http.cookies.set(
                "user_session",
                user_session,
                path="/",
                domain="nicovideo.jp")
            self.save_cookies()
            return True

        elif email is not None and password is not None:
            _log.info("Email and password are provided. Attemping login.")

            payload = {"mail_tel": email, "password": password}
            resp = self.session.http.post(_login_url, data=payload,
                                          params=_login_url_params)

            _log.debug("Login response code: {0}".format(resp.status_code))
            _log.trace("Login response body: {0}".format(resp.text))
            _log.debug("Cookies: {0}".format(
                self.session.http.cookies.get_dict()))

            if self.session.http.cookies.get("user_session") is None:
                try:
                    msg = extract_text(
                        resp.text, '<p class="notice__text">', "</p>")
                except Exception as e:
                    _log.debug(e)
                    msg = "unknown reason"
                _log.warning("Login failed. {0}".format(msg))
                return False
            else:
                _log.info("Logged in.")
                self.save_cookies()
                return True
        else:
            _log.warning(
                "Neither a email and password combination nor a user session "
                "token is provided. Cannot attempt login.")
            return False


class NicoHLSStream(HLSStream):

    def __init__(self, hls_stream, nicolive_plugin):
        super().__init__(
            hls_stream.session,
            force_restart=hls_stream.force_restart,
            start_offset=hls_stream.start_offset,
            duration=hls_stream.duration,
            **hls_stream.args)
        # url is already in hls_stream.args

        self.nicolive_plugin = nicolive_plugin

    def open(self):
        reader = super().open()
        self.nicolive_plugin.stream_reader = reader
        return reader


def extract_text(text, left, right):
    """Extract text from HTML"""
    result = re.findall("{0}(.*?){1}".format(left, right), text)
    if len(result) != 1:
        raise Exception("Failed to extract string. "
                        "Expected 1, found {0}".format(len(result)))
    return result[0]


def parse_proxy_url(purl):
    """Adapted from UStreamTV plugin (ustreamtv.py)"""

    proxy_options = {}
    if purl:
        p = urlparse(purl)
        proxy_options['proxy_type'] = p.scheme
        proxy_options['http_proxy_host'] = p.hostname
        if p.port:
            proxy_options['http_proxy_port'] = p.port
        if p.username:
            proxy_options['http_proxy_auth'] = \
                (unquote_plus(p.username), unquote_plus(p.password or ""))
    return proxy_options


__plugin__ = NicoLive
