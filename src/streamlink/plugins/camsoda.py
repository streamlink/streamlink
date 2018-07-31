import logging
import random
import re

from streamlink.exceptions import PluginError
from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class Camsoda(Plugin):
    API_URL_USER = "https://www.camsoda.com/api/v1/user/{0}"
    API_URL_VIDEO = "https://www.camsoda.com/api/v1/video/vtoken/{0}?username=guest_{1}"
    HLS_URL_VIDEO = "https://{server}/{app}/mp4:{stream_name}_aac/playlist.m3u8?token={token}"

    _url_re = re.compile(r"https?://(?:www\.)?camsoda\.com/(?P<username>[^/]+/?$)")

    _user_schema = validate.Schema(
        {
            "status": bool,
            "user": {
                "chat": {
                    "status": validate.text,
                    "stream_name": validate.text,
                    "origin_server": validate.text,
                    "slug": validate.text,
                }
            }
        }
    )

    _error_schema = validate.Schema(
        {
            "status": bool,
            "error": validate.text
        }
    )

    _api_video_schema = validate.Schema(
        {
            "token": validate.text,
            "app": validate.text,
            "edge_servers": [validate.text],
            "stream_name": validate.text
        }
    )

    _api_schema = validate.Schema(
        validate.any(_user_schema, _error_schema)
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _stream_status(self, data_user):
        log.trace("{0!r}".format(data_user))
        if not data_user["status"]:
            raise PluginError(data_user["error"])

        user_status = data_user["user"]["chat"]["status"]
        is_online = user_status == "online"
        if not is_online:
            raise PluginError("status - {0}".format(user_status))

    def _get_streams(self):
        self.session.http.headers.update({"User-Agent": useragents.FIREFOX})
        username = self._url_re.match(self.url).group("username")

        res = self.session.http.get(self.API_URL_USER.format(username))
        data_user = self.session.http.json(res, schema=self._api_schema)
        self._stream_status(data_user)

        res = self.session.http.get(
            self.API_URL_VIDEO.format(username, random.randint(1000, 99999)))
        data_video = self.session.http.json(res, schema=self._api_video_schema)
        log.trace("{0!r}".format(data_video))
        hls_url = self.HLS_URL_VIDEO.format(
            server=data_video["edge_servers"][0],
            app=data_video["app"],
            stream_name=data_video["stream_name"],
            token=data_video["token"]
        )
        for s in HLSStream.parse_variant_playlist(self.session, hls_url).items():
            yield s


__plugin__ = Camsoda
