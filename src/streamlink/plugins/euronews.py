"""
$description French television news network, covering world news from the European perspective.
$url euronews.com
$type live
"""

import re
from urllib.parse import urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream
from streamlink.utils.url import update_scheme


@pluginmatcher(re.compile(
    r'https?://(?:(?P<subdomain>\w+)\.)?euronews\.com/'
))
class Euronews(Plugin):
    API_URL = "https://{subdomain}.euronews.com/api/watchlive.json"

    def _get_vod_stream(self):
        root = self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html()
        ))

        video_url = root.xpath("string(.//meta[@property='og:video'][1]/@content)")
        if video_url:
            return dict(vod=HTTPStream(self.session, video_url))

        video_id = root.xpath("string(.//div[@data-google-src]/@data-video-id)")
        if video_id:
            return self.session.streams(f"https://www.youtube.com/watch?v={video_id}")

        video_url = root.xpath("string(.//iframe[@id='pfpPlayer'][starts-with(@src,'https://www.youtube.com/')][1]/@src)")
        if video_url:
            return self.session.streams(video_url)

    def _get_live_streams(self):
        video_id = self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string(".//div[@data-google-src]/@data-video-id")
        ))

        if video_id:
            return self.session.streams(f"https://www.youtube.com/watch?v={video_id}")

        info_url = self.session.http.get(self.API_URL.format(subdomain=self.match.group("subdomain")), schema=validate.Schema(
            validate.parse_json(),
            {"url": validate.url()},
            validate.get("url"),
            validate.transform(lambda url: update_scheme("https://", url))
        ))
        hls_url = self.session.http.get(info_url, schema=validate.Schema(
            validate.parse_json(),
            {
                "status": "ok",
                "protocol": "hls",
                "primary": validate.url()
            },
            validate.get("primary")
        ))

        return HLSStream.parse_variant_playlist(self.session, hls_url)

    def _get_streams(self):
        parsed = urlparse(self.url)

        if parsed.path == "/live":
            return self._get_live_streams()
        else:
            return self._get_vod_stream()


__plugin__ = Euronews
