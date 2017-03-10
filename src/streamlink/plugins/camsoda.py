import random
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HLSStream

API_USER_URL = "https://www.camsoda.com/api/v1/user/{0}"
API_VIDEO_URL = "https://www.camsoda.com/api/v1/video/vtoken/{0}?username=guest_{1}"

HLS_VIDEO_URL = "https://{server}/{app}/mp4:{stream_name}_mjpeg/playlist.m3u8?token={token}"

_url_re = re.compile(r"http(s)?://(www\.)?camsoda\.com/(?P<username>.+)")

_api_user_schema = validate.Schema(
    {
        "status": validate.any(int, validate.text),
        validate.optional("user"): {
            "settings": {
                "cam_password": validate.any(int, validate.text),
            },
            "online": validate.any(int, validate.text),
            "chatstatus": validate.text,
        }
    }
)

_api_video_schema = validate.Schema(
    {
        "token": validate.text,
        "app": validate.text,
        "edge_servers": [validate.text],
        "private_servers": [validate.text],
        "mjpeg_server": validate.text,
        "stream_name": validate.text
    }
)


class Camsoda(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        username = match.group("username")
        username = username.replace("/", "")

        res = http.get(API_USER_URL.format(username))
        data_user = http.json(res, schema=_api_user_schema)

        found_username = data_user["status"] is True
        if found_username is False:
            self.logger.info("No validate username found for {0}".format(self.url))
            return

        is_online = data_user["user"]["online"] is True
        if is_online is False:
            self.logger.info("This stream is currently offline")
            return

        is_protected = data_user["user"]["settings"]["cam_password"] is True
        if is_protected:
            self.logger.info("Stream is protected with a password")
            return

        res = http.get(API_VIDEO_URL.format(username, str(random.randint(1000, 99999))))
        data_video = http.json(res, schema=_api_video_schema)

        is_edge = data_user["user"]["chatstatus"] == "online"
        is_priv = data_user["user"]["chatstatus"] == "private"

        if is_edge:
            server = data_video["edge_servers"][0]
        elif is_priv:
            server = data_video["private_servers"][0]
        else:
            server = data_video["mjpeg_server"]

        hls_url = HLS_VIDEO_URL.format(server=server, app=data_video["app"], stream_name=data_video["stream_name"], token=data_video["token"])

        try:
            for s in HLSStream.parse_variant_playlist(self.session, hls_url).items():
                yield s
        except IOError as err:
            self.logger.warning("Error parsing stream: {0}", err)

__plugin__ = Camsoda
