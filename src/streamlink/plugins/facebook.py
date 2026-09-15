"""
$description Global live-streaming and video hosting social platform.
$url facebook.com
$type live, vod
$metadata title
"""

import re
import uuid
from urllib.parse import urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import useragents, validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.http import HTTPStream
from streamlink.utils import parse


@pluginmatcher(
    name="default", pattern=re.compile(r"https://www.facebook.com/(?P<user>[^/]+)/videos/(?:[^/]+/)?(?P<video_id>\d+)")
)
@pluginmatcher(
    name="search",
    pattern=re.compile(r"https://www.facebook.com/watch/(?:live/)?\?ref=watch_permalink&v=(?P<video_id>\d+)"),
)
@pluginmatcher(
    name="share",
    pattern=re.compile(r"https://www.facebook.com/share/[vr]/(?P<share_id>[^/]+)"),
)
class Facebook(Plugin):
    def _get_meta(self, html):
        self.id = self.match.group("video_id") if not self.matches["share"] else self.match.group("share_id")
        self.title = validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string('.//meta[@name="description"]/@content'),
            validate.transform(lambda x: x.split("\n")[0] if isinstance(x, str) else x),
        ).validate(html)

        if self.matches["default"] and not (user := self.match.group("user")).isdigit() and user != "_":
            self.author = user
            return

        owner_schema = validate.Schema(
            validate.parse_json(),
            validate.any(
                {"name": str},
                {},
            ),
            validate.none_or_all(
                validate.get("name"),
            ),
        )

        for match in re.finditer(r'"(?:owner_as_page|video_owner|author)"\s*:\s*(\{[^{}]*})', html):
            author = owner_schema.validate(match.group(1))
            if author:
                self.author = author
                break

    def _get_streams(self):
        if not self.matches["share"]:
            user = self.match.groupdict().get("user") or "_"
            video_id = self.match.group("video_id")
            self.url = f"https://www.facebook.com/{user}/videos/{video_id}"

        headers = {
            "User-Agent": useragents.FIREFOX,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Alt-Used": "www.facebook.com",
            "Sec-Fetch-Site": "none",
        }
        response = self.session.http.get(self.url, headers=headers)
        text = response.text.replace(r"\/", "/").replace("&amp;", "&")
        dash_manifest_urls = re.findall(r'"dash_manifest_url":"(.*?)"', text)
        browser_native_urls = re.findall(r'"(?:browser_native_sd_url|browser_native_hd_url)"\s*:\s*"([^"]*)"', text)
        self._get_meta(response.text)

        for dash_url in dash_manifest_urls:
            if dash_url and "dummy" not in urlparse(dash_url).query:
                yield from DASHStream.parse_manifest(self.session, dash_url).items()

        for vod_url in browser_native_urls:
            parsed_vod_url = urlparse(vod_url)
            if isinstance(vod_url, str) and parsed_vod_url.path.endswith(".mp4"):
                yield (
                    parse.parse_qsd(parsed_vod_url.query).get("tag", uuid.uuid4()).replace("-", "_"),
                    HTTPStream(self.session, vod_url),
                )


__plugin__ = Facebook
