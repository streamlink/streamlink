import random
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream

_url_re = re.compile(r"http(s)?://(www\.)?camsoda\.com/(?P<username>[^\"\']+)")

_api_user_schema = validate.Schema(
    {
        "status": validate.any(int, validate.text),
        validate.optional("user"): {
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
    API_URL_USER = "https://www.camsoda.com/api/v1/user/{0}"
    API_URL_VIDEO = "https://www.camsoda.com/api/v1/video/vtoken/{0}?username=guest_{1}"
    HLS_URL_VIDEO = "https://{server}/{app}/mp4:{stream_name}_mjpeg/playlist.m3u8?token={token}"

    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _stream_status(self, data_user):
        invalid_username = data_user["status"] is False
        if invalid_username:
            self.logger.info("No validate username found for {0}".format(self.url))
            return

        is_offline = data_user["user"]["online"] is False
        if is_offline:
            self.logger.info("This stream is currently offline")
            return

        return True

    def _get_api_user(self, username):
        res = http.get(self.API_URL_USER.format(username))
        data_user = http.json(res, schema=_api_user_schema)
        return data_user

    def _get_api_video(self, username):
        res = http.get(self.API_URL_VIDEO.format(username, str(random.randint(1000, 99999))))
        data_video = http.json(res, schema=_api_video_schema)
        return data_video

    def _get_hls_url(self, data_user, data_video):
        is_edge = data_user["user"]["chatstatus"] == "online"
        is_priv = data_user["user"]["chatstatus"] == "private"
        if is_edge:
            server = data_video["edge_servers"][0]
        elif is_priv:
            server = data_video["private_servers"][0]
        else:
            server = data_video["mjpeg_server"]

        hls_url = self.HLS_URL_VIDEO.format(server=server, app=data_video["app"], stream_name=data_video["stream_name"], token=data_video["token"])
        return hls_url

    def _get_streams(self):
        match = _url_re.match(self.url)
        username = match.group("username")
        username = username.replace("/", "")

        data_user = self._get_api_user(username)
        stream_status = self._stream_status(data_user)

        if stream_status:
            data_video = self._get_api_video(username)
            hls_url = self._get_hls_url(data_user, data_video)

            try:
                for s in HLSStream.parse_variant_playlist(self.session, hls_url).items():
                    yield s
            except IOError as err:
                self.logger.error("Error parsing stream: {0}", err)

__plugin__ = Camsoda
