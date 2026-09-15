"""
$description Global live-streaming and video hosting social platform owned by Meta Platforms, Inc.
$url facebook.com
$type live, vod
$metadata id
$metadata author
$metadata title
"""

import re
from urllib.parse import parse_qsl, urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.http import HTTPStream
from streamlink.utils.data import search_dict
from streamlink.utils.num import to_float


@pluginmatcher(
    name="default",
    pattern=re.compile(
        r"https?://(?:www\.)?facebook\.com/(?:(?P<user>[^/]+)/)?(?:videos?|reel?)/?(?:[^/]+/)?(?P<video_id>\d+)",
    ),
)
@pluginmatcher(
    name="search",
    pattern=re.compile(r"https?://(?:www\.)?facebook\.com/watch/(?:live/)?\?ref=watch_permalink&v=(?P<video_id>\d+)"),
)
@pluginmatcher(
    name="share",
    pattern=re.compile(r"https?://(?:www\.)?facebook\.com/share/[vr]/(?P<share_id>[^/]+)"),
)
class Facebook(Plugin):
    _HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Sec-Fetch-Site": "none",
    }

    _SCHEMA_CONTENT = validate.Schema(
        validate.parse_html(),
        validate.union((
            validate.all(
                validate.xml_xpath_string(".//meta[@name='description'][1]/@content"),
                validate.none_or_all(
                    validate.transform(lambda x: x.split("\n")[0]),
                ),
            ),
            validate.any(
                *[
                    validate.all(
                        validate.xml_xpath_string(
                            ".//script[@type='application/json'][contains(text(),$key)][1]/text()",
                            key=f'"{key}"',
                        ),
                        validate.none_or_all(
                            validate.parse_json(),
                            validate.transform(lambda d, k: next(search_dict(d, k), None), key),
                            {validate.optional("name"): str},
                            validate.get("name"),
                        ),
                    )
                    for key in (
                        "owner_as_page",
                        "video_owner",
                        "author",
                    )
                ],
                validate.transform(lambda _: None),
            ),
            *[
                validate.all(
                    validate.xml_xpath_string(
                        ".//script[@type='application/json'][contains(text(),$key)][1]/text()",
                        key=f'"{key}"',
                    ),
                    validate.none_or_all(
                        validate.parse_json(),
                        validate.transform(lambda d, k: next(search_dict(d, k), None), key),
                    ),
                )
                for key in (
                    "dash_manifest_url",
                    "browser_native_sd_url",
                    "browser_native_hd_url",
                )
            ],
        )),
    )

    def _get_streams(self):
        if self.matches["share"]:
            self.id = self.match.group("share_id")
        else:
            match = self.match.groupdict()
            self.id = self.match.group("video_id")
            self.url = f"https://www.facebook.com/{match.get('user') or '_'}/videos/{self.id}"

        self.title, self.author, *url_data = self.session.http.get(
            self.url,
            headers=self._HEADERS,
            schema=self._SCHEMA_CONTENT,
        )

        if not self.author and self.matches["default"] and re.match(r"\D", (user := self.match.group("user"))) and user != "_":
            self.author = user

        for url in url_data:
            if not url:
                continue
            parsed_url = urlparse(url)

            if parsed_url.path.endswith(".mpd") and "dummy" not in parsed_url.query:
                yield from DASHStream.parse_manifest(self.session, url).items()
                break

            if parsed_url.path.endswith(".mp4"):
                bitrate = dict(parse_qsl(parsed_url.query)).get("bitrate")
                if not bitrate or not (parsed_bitrate := to_float(bitrate)):
                    continue
                yield f"{parsed_bitrate / 1000:.0f}k", HTTPStream(self.session, url)


__plugin__ = Facebook
