"""
$description Live TV channel and video on-demand service from TV5Monde, a French free-to-air broadcaster.
$url tv5monde.com
$url tivi5mondeplus.com
$type live, vod
$region France, Belgium, Switzerland
"""

import re
from urllib.parse import urlparse

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream
from streamlink.utils.url import update_scheme


@pluginmatcher(re.compile(r"""
    https?://(?:[\w-]+\.)*(?:tv5monde|tivi5mondeplus)\.com/
""", re.VERBOSE))
class TV5Monde(Plugin):
    def _get_hls(self, root):
        schema_live = validate.Schema(
            validate.xml_xpath_string(".//*[contains(@data-broadcast,'m3u8')]/@data-broadcast"),
            str,
            validate.parse_json(),
            validate.any(
                validate.all({"files": list}, validate.get("files")),
                list
            ),
            [{
                "url": validate.url(path=validate.endswith(".m3u8"))
            }],
            validate.get((0, "url")),
            validate.transform(lambda content_url: update_scheme("https://", content_url))
        )
        try:
            live = schema_live.validate(root)
        except PluginError:
            return

        return HLSStream.parse_variant_playlist(self.session, live)

    def _get_vod(self, root):
        schema_vod = validate.Schema(
            validate.xml_xpath_string(".//script[@type='application/ld+json'][contains(text(),'VideoObject')][1]/text()"),
            str,
            validate.transform(lambda jsonlike: re.sub(r"[\r\n]+", "", jsonlike)),
            validate.parse_json(),
            validate.any(
                validate.all(
                    {"@graph": [dict]},
                    validate.get("@graph"),
                    validate.filter(lambda obj: obj["@type"] == "VideoObject"),
                    validate.get(0)
                ),
                dict
            ),
            {"contentUrl": validate.url()},
            validate.get("contentUrl"),
            validate.transform(lambda content_url: update_scheme("https://", content_url))
        )
        try:
            vod = schema_vod.validate(root)
        except PluginError:
            return

        if urlparse(vod).path.endswith(".m3u8"):
            return HLSStream.parse_variant_playlist(self.session, vod)

        return {"vod": HTTPStream(self.session, vod)}

    def _get_streams(self):
        root = self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html()
        ))

        return self._get_hls(root) or self._get_vod(root)


__plugin__ = TV5Monde
