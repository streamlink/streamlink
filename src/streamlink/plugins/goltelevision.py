import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?goltelevision\.com/live"
))
class GOLTelevision(Plugin):
    api_url = "https://api.goltelevision.com/api/v1/media/hls/service/live"
    api_schema = validate.Schema(validate.transform(parse_json), {
        "code": 200,
        "message": {
            "success": {
                "manifest": validate.url()
            }
        }
    }, validate.get("message"), validate.get("success"), validate.get("manifest"))

    def _get_streams(self):
        return HLSStream.parse_variant_playlist(self.session,
                                                self.session.http.get(self.api_url, schema=self.api_schema))


__plugin__ = GOLTelevision
