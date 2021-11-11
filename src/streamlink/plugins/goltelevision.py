import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


class GOLTelevisionHLSStream(HLSStream):
    @classmethod
    def _get_variant_playlist(cls, res):
        res.encoding = "UTF-8"
        return super()._get_variant_playlist(res)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?goltelevision\.com/en-directo"
))
class GOLTelevision(Plugin):
    def _get_streams(self):
        url = self.session.http.get(
            "https://www.goltelevision.com/api/manifest/live",
            schema=validate.Schema(
                validate.parse_json(),
                {"manifest": validate.url()},
                validate.get("manifest")
            )
        )
        return GOLTelevisionHLSStream.parse_variant_playlist(self.session, url)


__plugin__ = GOLTelevision
