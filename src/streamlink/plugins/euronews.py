import re
from urllib.parse import urlparse

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.plugin.api.utils import itertags
from streamlink.stream import HTTPStream


class Euronews(Plugin):
    _url_re = re.compile(r'https?://(?:\w+\.)*euronews\.com/')

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

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

    def _get_streams(self):
        parsed = urlparse(self.url)

        if parsed.path == "/live":
            return self._get_live_streams()
        else:
            return self._get_vod_stream()


__plugin__ = Euronews
