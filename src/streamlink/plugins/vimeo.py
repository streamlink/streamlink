"""
$description Global live-streaming and video hosting social platform.
$url vimeo.com
$type live, vod
$notes Password protected streams are not supported
"""

import logging
import re
from urllib.parse import urljoin, urlparse

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
    pattern=re.compile(r"https?://(?:www\.)?vimeo\.com/.+"),
)
@pluginmatcher(
    name="player",
    pattern=re.compile(r"https?://player\.vimeo\.com/video/\d+"),
)
class Vimeo(Plugin):
    VIEWER_URL = "https://vimeo.com/_next/viewer"
    OEMBED_URL = "https://vimeo.com/api/oembed.json"

    @staticmethod
    def _schema_config(config):
        schema_cdns = validate.all(
            {
                "cdns": {
                    str: validate.all(
                        {"url": validate.url()},
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
                                    "url": validate.url(),
                                    "quality": str,
                                },
                                validate.union_get("quality", "url"),
                            ),
                        ],
                    },
                    validate.optional("text_tracks"): [
                        validate.all(
                            {
                                "url": str,
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
        return self.session.http.get(url, schema=validate.Schema(
            validate.parse_json(),
            {"url": validate.url()},
            validate.get("url"),
        ))

    def _query_player(self):
        return self.session.http.get(self.url, schema=validate.Schema(
            re.compile(r"playerConfig\s*=\s*({.+?})\s*var"),
            validate.none_or_all(
                validate.get(1),
                validate.parse_json(),
                validate.transform(self._schema_config),
            ),
        ))

    def _query_api(self):
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
                {"uri": str},
                validate.get("uri"),
            ),
        )
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

        return self.session.http.get(config_url, schema=validate.Schema(
            validate.parse_json(),
            validate.transform(self._schema_config),
        ))

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

        for url in hls.values():
            streams.extend(HLSStream.parse_variant_playlist(self.session, url).items())
            break

        for url in dash.values():
            p = urlparse(url)
            if p.path.endswith("dash.mpd"):
                # LIVE
                url = self._get_dash_url(url)
            elif p.path.endswith("master.json"):
                # VOD
                url = url.replace("master.json", "master.mpd")
            else:
                log.error(f"Unsupported DASH path: {p.path}")
                continue

            streams.extend(DASHStream.parse_manifest(self.session, url).items())
            break

        streams.extend(
            (quality, HTTPStream(self.session, url))
            for quality, url in progressive or []
        )

        if text_tracks and self.session.get_option("mux-subtitles"):
            substreams = {
                lang: HTTPStream(self.session, urljoin("https://vimeo.com/", url))
                for lang, url in text_tracks
            }
            for quality, stream in streams:
                yield quality, MuxedStream(self.session, stream, subtitles=substreams)
        else:
            yield from streams


__plugin__ = Vimeo
