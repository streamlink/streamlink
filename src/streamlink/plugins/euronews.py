import re
from urllib.parse import urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.plugin.api.utils import itertags, parse_json
from streamlink.stream import HLSStream, HTTPStream
from streamlink.utils import update_scheme


@pluginmatcher(re.compile(
    r'https?://(?:(?P<subdomain>\w+)\.)?euronews\.com/'
))
class Euronews(Plugin):
    API_URL = "https://{subdomain}.euronews.com/api/watchlive.json"

    def _get_vod_stream(self):
        def find_video_url(content):
            for elem in itertags(content, "meta"):
                if elem.attributes.get("property") == "og:video":
                    return elem.attributes.get("content")

        video_url = self.session.http.get(self.url, schema=validate.Schema(
            validate.transform(find_video_url),
            validate.any(None, validate.url())
        ))

        if video_url is not None:
            return dict(vod=HTTPStream(self.session, video_url))

    def _get_live_streams(self):
        def find_video_id(content):
            for elem in itertags(content, "div"):
                if elem.attributes.get("id") == "pfpPlayer" and elem.attributes.get("data-google-src") is not None:
                    return elem.attributes.get("data-video-id")

        video_id = self.session.http.get(self.url, schema=validate.Schema(
            validate.transform(find_video_id),
            validate.any(None, str)
        ))

        if video_id is not None:
            return self.session.streams(f"https://www.youtube.com/watch?v={video_id}")

        info_url = self.session.http.get(self.API_URL.format(subdomain=self.match.group("subdomain")), schema=validate.Schema(
            validate.transform(parse_json),
            {"url": validate.url()},
            validate.get("url"),
            validate.transform(lambda url: update_scheme("https://", url))
        ))
        hls_url = self.session.http.get(info_url, schema=validate.Schema(
            validate.transform(parse_json),
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
