"""
$description Global live-streaming and video hosting social platform.
$url vimeo.com
$type live, vod
$metadata id
$metadata author
$metadata title
$notes Password protected streams are not supported
"""

import logging
import re
from urllib.parse import urljoin, urlparse

from streamlink.exceptions import NoStreamsError
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.ffmpegmux import MuxedStream
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream
from streamlink.utils.url import update_scheme


log = logging.getLogger(__name__)


@pluginmatcher(
    name="default",
    pattern=re.compile(r"https?://(?:www\.)?vimeo\.com/(?!event/).+"),
)
@pluginmatcher(
    name="event",
    pattern=re.compile(r"https?://(?:www\.)?vimeo\.com/event/(?P<event_id>\d+)"),
)
@pluginmatcher(
    name="player",
    pattern=re.compile(r"https?://player\.vimeo\.com/video/\d+"),
)
class Vimeo(Plugin):
    VIEWER_URL = "https://vimeo.com/_next/viewer"
    OEMBED_URL = "https://vimeo.com/api/oembed.json"
    EVENT_EMBED_URL = "https://vimeo.com/event/{id}/embed"

    @staticmethod
    def _schema_config(config):
        schema_cdns = validate.all(
            {
                "cdns": {
                    str: validate.all(
                        {validate.optional("url"): validate.url()},
                        validate.get("url"),
                    ),
                },
            },
            validate.get("cdns"),
        )
        schema_config = validate.Schema(
            {
                "request": {
                    "files": {
                        validate.optional("hls"): schema_cdns,
                        validate.optional("dash"): schema_cdns,
                        validate.optional("progressive"): [
                            validate.all(
                                {
                                    validate.optional("url"): validate.url(),
                                    "quality": str,
                                },
                                validate.union_get("quality", "url"),
                            ),
                        ],
                    },
                    validate.optional("text_tracks"): [
                        validate.all(
                            {
                                validate.optional("url"): str,
                                "lang": str,
                            },
                            validate.union_get("lang", "url"),
                        ),
                    ],
                },
                validate.optional("video"): validate.none_or_all(
                    {
                        "id": int,
                        "title": str,
                        "owner": {
                            "name": str,
                        },
                    },
                    validate.union_get(
                        "id",
                        ("owner", "name"),
                        "title",
                    ),
                ),
            },
            validate.union_get(
                ("request", "files", "hls"),
                ("request", "files", "dash"),
                ("request", "files", "progressive"),
                ("request", "text_tracks"),
                "video",
            ),
        )

        return schema_config.validate(config)

    def _get_dash_url(self, url):
        return self.session.http.get(
            url,
            schema=validate.Schema(
                validate.parse_json(),
                {"url": validate.url()},
                validate.get("url"),
            ),
        )

    def _query_player(self):
        return self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//script[contains(text(),'window.playerConfig')][1]/text()"),
                validate.none_or_all(
                    re.compile(r"^\s*window\.playerConfig\s*=\s*(?P<json>{.+?})\s*$"),
                    validate.none_or_all(
                        validate.get("json"),
                        validate.parse_json(),
                        validate.transform(self._schema_config),
                    ),
                ),
            ),
        )

    def _get_config_url(self):
        jwt, api_url = self.session.http.get(
            self.VIEWER_URL,
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "jwt": str,
                    "apiUrl": str,
                },
                validate.union_get("jwt", "apiUrl"),
            ),
        )
        uri = self.session.http.get(
            self.OEMBED_URL,
            params={"url": self.url},
            schema=validate.Schema(
                validate.parse_json(),
                {validate.optional("uri"): str},
                validate.get("uri"),
            ),
        )
        if not uri:
            return

        player_config_url = urljoin(update_scheme("https://", api_url), uri)
        config_url = self.session.http.get(
            player_config_url,
            params={"fields": "config_url"},
            headers={"Authorization": f"jwt {jwt}"},
            schema=validate.Schema(
                validate.parse_json(),
                {"config_url": validate.url()},
                validate.get("config_url"),
            ),
        )

        return config_url

    def _get_config_url_event(self):
        return self.session.http.get(
            self.EVENT_EMBED_URL.format(id=self.match["event_id"]),
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//script[contains(text(),'var htmlString')][1]/text()"),
                validate.none_or_all(
                    re.compile(r"var htmlString\s*=\s*`(?P<html>.+?)`;", re.DOTALL),
                    validate.none_or_all(
                        validate.get("html"),
                        validate.parse_html(),
                        validate.xml_xpath_string(".//*[@data-config-url][1]/@data-config-url"),
                    ),
                ),
            ),
        )

    def _query_api(self):
        config_url = ""
        if self.matches["event"]:
            log.debug("Getting event config_url")
            config_url = self._get_config_url_event()
        if not config_url:
            log.debug("Getting config_url")
            config_url = self._get_config_url()

        if not config_url:
            log.error("The content is not available")
            raise NoStreamsError

        return self.session.http.get(
            config_url,
            schema=validate.Schema(
                validate.parse_json(),
                validate.transform(self._schema_config),
            ),
        )

    def _get_streams(self):
        if self.matches["player"]:
            data = self._query_player()
        else:
            data = self._query_api()

        if not data:
            return

        hls, dash, progressive, text_tracks, metadata = data
        if metadata:
            self.id, self.author, self.title = metadata

        streams = []

        hls = hls or {}
        for url in hls.values():
            if not url:
                continue
            streams.extend(HLSStream.parse_variant_playlist(self.session, url).items())
            break

        dash = dash or {}
        for url in dash.values():
            if not url:
                continue
            # DASH manifests (sometimes?) are in the JSON format, which is unsupported.
            # Previously, it was possible to change the URL's path component and replace the manifest's file name extension,
            # but now, URLs are signed and can't be updated anymore, so simply discard those kinds of DASH manifest URLs.
            p = urlparse(url)
            if not p.path.endswith("dash.mpd"):
                continue
            url = self._get_dash_url(url)

            streams.extend(DASHStream.parse_manifest(self.session, url).items())
            break

        streams.extend(
            (quality, HTTPStream(self.session, url))
            for quality, url in progressive or []
            if url and quality not in streams
        )  # fmt: skip

        if text_tracks and self.session.get_option("mux-subtitles"):
            substreams = {
                lang: HTTPStream(self.session, urljoin("https://vimeo.com/", url))
                for lang, url in text_tracks
                if url
            }  # fmt: skip
            for quality, stream in streams:
                yield quality, MuxedStream(self.session, stream, subtitles=substreams)
        else:
            yield from streams


__plugin__ = Vimeo
