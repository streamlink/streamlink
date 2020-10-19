import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json


class GOLTelevision(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?goltelevision\.com/live")
    api_url = "https://api.goltelevision.com/api/v1/media/hls/service/live"
    api_schema = validate.Schema(validate.transform(parse_json), {
        "code": 200,
        "message": {
            "success": {
                "manifest": validate.url()
            }
        }
    }, validate.get("message"), validate.get("success"), validate.get("manifest"))

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        return HLSStream.parse_variant_playlist(self.session,
                                                self.session.http.get(self.api_url, schema=self.api_schema))


__plugin__ = GOLTelevision
