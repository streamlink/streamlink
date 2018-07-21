import logging
import re

from streamlink.exceptions import PluginError
from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import RTMPStream

log = logging.getLogger(__name__)


class YouNow(Plugin):

    user_api_url = "https://api.younow.com/php/api/broadcast/info/curId=0/user={0}"

    _url_re = re.compile(r"https?://(?:\w+\.)?younow\.com/(?P<channel>[^/&?]+)")

    _user_schema = validate.Schema(
        {
            "errorCode": int,
            "media": {
                "host": validate.text,
                "app": validate.text,
                "stream": validate.text
            },
            "title": validate.text,
            "username": validate.text
        }
    )

    _error_schema = validate.Schema(
        {
            "errorCode": int,
            "errorMsg": validate.text
        }
    )

    _api_schema = validate.Schema(
        validate.any(_user_schema, _error_schema)
    )

    author = None
    title = None

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def get_author(self):
        if self.author is None:
            self.get_api_data()
        return self.author

    def get_title(self):
        if self.title is None:
            self.get_api_data()
        return self.title

    def get_api_data(self):
        match = self._url_re.match(self.url)
        channel = match.group("channel")

        res = self.session.http.get(self.user_api_url.format(channel))
        data = self.session.http.json(res, schema=self._api_schema)
        log.trace("{0!r}".format(data))

        if data["errorCode"] != 0:
            raise PluginError("{0} - {1}".format(data["errorCode"], data["errorMsg"]))

        self.author = data["username"]
        self.title = data["title"]

        return data

    def _get_streams(self):
        data = self.get_api_data()
        params = {
            "rtmp": "rtmp://{0}{1}/{2}".format(data["media"]["host"],
                                               data["media"]["app"],
                                               data["media"]["stream"]),
            "live": True
        }
        return {"live": RTMPStream(self.session, params=params)}


__plugin__ = YouNow
