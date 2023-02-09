"""
$description Internet portal in Estonia, Latvia, and Lithuania providing daily news, ranging from gardening to politics.
$url delfi.lt
$url delfi.ee
$url delfi.lv
$type vod
"""

import itertools
import logging
import re
from urllib.parse import urlparse

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.utils.parse import parse_qsd
from streamlink.utils.url import update_scheme


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:[\w-]+\.)?delfi\.(?P<tld>lt|lv|ee)",
))
class Delfi(Plugin):
    _api = {
        "lt": "https://g2.dcdn.lt/vfe/data.php",
        "lv": "https://g.delphi.lv/vfe/data.php",
        "ee": "https://g4.nh.ee/vfe/data.php",
    }

    def _get_streams_api(self, video_id):
        log.debug(f"Found video ID: {video_id}")

        tld = self.match.group("tld")
        try:
            data = self.session.http.get(
                self._api.get(tld, "lt"),
                params=dict(video_id=video_id),
                schema=validate.Schema(
                    validate.parse_json(),
                    {
                        "success": True,
                        "data": {
                            "versions": {
                                str: validate.all(
                                    [{
                                        "type": str,
                                        "src": str,
                                    }],
                                    validate.filter(lambda item: item["type"] == "application/x-mpegurl"),
                                ),
                            },
                        },
                    },
                    validate.get(("data", "versions")),
                ),
            )
        except PluginError:
            log.error("Failed to get streams from API")
            return

        for stream in itertools.chain(*data.values()):
            src = update_scheme("https://", stream["src"], force=False)
            yield from HLSStream.parse_variant_playlist(self.session, src).items()

    def _get_streams_delfi(self, src):
        try:
            data = self.session.http.get(src, schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//script[contains(text(),'embedJs.setAttribute(')][1]/text()"),
                validate.none_or_all(
                    re.compile(r"embedJs\.setAttribute\('src',\s*'(.+?)'"),
                    validate.none_or_all(
                        validate.get(1),
                        validate.transform(lambda url: parse_qsd(urlparse(url).fragment)),
                        {"stream": str},
                        validate.get("stream"),
                        validate.parse_json(),
                        {"versions": [{
                            "hls": str,
                        }]},
                        validate.get("versions"),
                    ),
                ),
            ))
        except PluginError:
            log.error("Failed to get streams from iframe")
            return

        for stream in data:
            src = update_scheme("https://", stream["hls"], force=False)
            yield from HLSStream.parse_variant_playlist(self.session, src).items()

    def _get_streams(self):
        root = self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html(),
        ))

        video_id = root.xpath("string(.//div[@data-provider='dvideo'][@data-id][1]/@data-id)")
        if video_id:
            return self._get_streams_api(str(video_id))

        yt_id = root.xpath("string(.//script[contains(@src,'/yt.js')][@data-video]/@data-video)")
        if yt_id:
            return self.session.streams(f"https://www.youtube.com/watch?v={yt_id}")

        yt_iframe = root.xpath("string(.//iframe[starts-with(@src,'https://www.youtube.com/')][1]/@src)")
        if yt_iframe:
            return self.session.streams(str(yt_iframe))

        delfi = root.xpath("string(.//iframe[@name='delfi-stream'][@src][1]/@src)")
        if delfi:
            return self._get_streams_delfi(str(delfi))


__plugin__ = Delfi
