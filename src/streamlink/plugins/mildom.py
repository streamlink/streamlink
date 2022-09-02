"""
$description Japanese live streaming and video hosting platform for live video game broadcasts and individual live streams.
$url mildom.com
$type live, vod
"""

import logging
import re
from time import time
from uuid import uuid4

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.utils.url import url_concat

log = logging.getLogger(__name__)


class MildomHLSStream(HLSStream):
    __shortname__ = "hls-mildom"
    expiry_time = 60 * 120

    def __init__(self, session_, api, server, token, quality, **args):
        self.session = session_
        self.api = api
        self.server = server
        self.token = token
        self.quality = quality
        self._url = self.build_hls_url()
        super().__init__(self.session, self._url, **args)
        self.expiry = time()

    def build_hls_url(self):
        if not self.server or not self.token:
            raise ValueError("server and token must be set")
        return url_concat(self.server, f"{self.api.channel_id}{self.quality}.m3u8?{self.token}")

    @property
    def url(self):
        if time() - self.expiry > MildomHLSStream.expiry_time:
            self.expiry = time()
            self.token = self.api.get_token()
            self._url = self.build_hls_url()
            log.debug("Updated HLS playlist URL query string")
        return self._url


class MildomAPI:
    def __init__(self, session, channel_id=None, video_id=None):
        self.session = session
        self.channel_id = channel_id
        self.video_id = video_id

    def _is_api_error(self, data):
        log.trace(f"{data!r}")
        if data["code"] != 0:
            log.debug(data.get("message", "Mildom API returned an error"))
            return True
        return False

    def get_vod_streams_data(self):
        if not self.video_id:
            return
        data = self.session.http.get(
            "https://cloudac.mildom.com/nonolive/videocontent/playback/getPlaybackDetail",
            params={
                "__platform": "web",
                "v_id": self.video_id,
            },
            schema=validate.Schema(validate.parse_json(), {
                "code": int,
                validate.optional("message"): str,
                validate.optional("body"): {
                    "playback": {
                        "video_link": [{"name": str, "url": validate.url()}],
                    },
                },
            })
        )
        if self._is_api_error(data):
            return
        if data.get("body"):
            return data["body"]["playback"]["video_link"]

    def get_token(self):
        if not self.channel_id:
            return
        data = self.session.http.post(
            "https://cloudac.mildom.com/nonolive/gappserv/live/token",
            params={
                "__platform": "web",
                "__guest_id": "pc-gp-{}".format(uuid4()),
            },
            headers={"Accept-Language": "en"},
            json={"host_id": self.channel_id, "type": "hls"},
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "code": int,
                    validate.optional("message"): str,
                    validate.optional("body"): {
                        "data": [
                            {"token": str, }
                        ],
                    }
                }
            )
        )
        if self._is_api_error(data):
            return
        if data.get("body"):
            return data["body"]["data"][0]["token"]

    def get_server(self):
        if not self.channel_id:
            return
        data = self.session.http.get(
            "https://cloudac.mildom.com/nonolive/gappserv/live/liveserver",
            params={
                "__platform": "web",
                "user_id": self.channel_id,
                "live_server_type": "hls",
            },
            headers={"Accept-Language": "en"},
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "code": int,
                    validate.optional("message"): str,
                    validate.optional("body"): {
                        "stream_server": validate.url(),
                    }
                }
            )
        )
        if self._is_api_error(data):
            return
        if data.get("body"):
            return data["body"]["stream_server"]

    def get_live_streams_data(self):
        if not self.channel_id:
            return
        data = self.session.http.get(
            "https://cloudac.mildom.com/nonolive/gappserv/live/enterstudio",
            params={
                "__platform": "web",
                "user_id": self.channel_id,
            },
            headers={"Accept-Language": "en"},
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "code": int,
                    validate.optional("message"): str,
                    validate.optional("body"): {
                        validate.optional("status"): int,
                        "anchor_live": int,
                        validate.optional("live_type"): int,
                        "ext": {
                            "cmode_params": [{
                                "cmode": str,
                                "name": str,
                            }],
                            validate.optional("live_mode"): int,
                        },
                    },
                },
            )
        )
        if self._is_api_error(data):
            return
        if data.get("body"):
            return data["body"]


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?mildom\.com/
    (?:
        playback/(\d+)(/(?P<video_id>(\d+)-(\w+)))
        |
        (?P<channel_id>\d+)
    )
""", re.VERBOSE))
class Mildom(Plugin):
    def _get_streams(self):
        api = MildomAPI(self.session, channel_id=self.match.group("channel_id"), video_id=self.match.group("video_id"))

        if api.video_id:
            data = api.get_vod_streams_data()
            if data:
                for stream in data:
                    yield stream["name"], HLSStream(self.session, stream["url"])
        else:
            data = api.get_live_streams_data()
            if not data:
                return

            if data["anchor_live"] != 11:
                log.debug("User doesn't appear to be live")
                return

            qualities = [
                (quality_info["name"], f"_{quality_info['cmode']}" if quality_info["cmode"] != "raw" else "")
                for quality_info in data["ext"]["cmode_params"]
            ]

            server = api.get_server()
            token = api.get_token()
            self.session.http.headers.update({"Referer": "https://www.mildom.com/"})
            for quality in qualities:
                yield quality[0], MildomHLSStream(self.session, api, server, token, quality[1])


__plugin__ = Mildom
