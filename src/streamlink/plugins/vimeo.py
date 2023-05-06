"""
$description Global live-streaming and video hosting social platform.
$url vimeo.com
$type live, vod
$notes Password protected streams are not supported
"""

import logging
import re
from html import unescape as html_unescape
from urllib.parse import urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.ffmpegmux import MuxedStream
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(player\.vimeo\.com/video/\d+|(www\.)?vimeo\.com/.+)",
))
class Vimeo(Plugin):
    VIEWER_URL = "https://vimeo.com/_next/viewer"
    OEMBED_URL = "https://vimeo.com/api/oembed.json"
    API_URL = "https://{0}/{1}?fields=config_url"
    _uri_schema = validate.Schema(
        validate.parse_json(),
        validate.all({
            "uri": str,
        }),
    )
    _viewer_schema = validate.Schema(
        validate.parse_json(),
        validate.all({
            "jwt": str,
            "apiUrl": str,
        }),
    )
    _config_url_re = re.compile(r'(?:"config_url"|\bdata-config-url)\s*[:=]\s*(".+?")')
    _config_re = re.compile(r"playerConfig\s*=\s*({.+?})\s*var")
    _config_url_schema = validate.Schema(
        validate.transform(_config_url_re.search),
        validate.any(
            None,
            validate.Schema(
                validate.get(1),
                validate.parse_json(),
                validate.transform(html_unescape),
                validate.url(),
            ),
        ),
    )
    _config_schema = validate.Schema(
        validate.parse_json(),
        {
            "request": {
                "files": {
                    validate.optional("dash"): {"cdns": {str: {"url": validate.url()}}},
                    validate.optional("hls"): {"cdns": {str: {"url": validate.url()}}},
                    validate.optional("progressive"): validate.all(
                        [{"url": validate.url(), "quality": str}],
                    ),
                },
                validate.optional("text_tracks"): validate.all(
                    [{"url": str, "lang": str}],
                ),
            },
        },
    )
    _player_schema = validate.Schema(
        validate.transform(_config_re.search),
        validate.any(None, validate.Schema(validate.get(1), _config_schema)),
    )

    def _get_streams(self):
        if "player.vimeo.com" in self.url:
            data = self.session.http.get(self.url, schema=self._player_schema)
        else:
            viewer = self.session.http.get(
                self.VIEWER_URL,
                schema=self._viewer_schema,
            )

            uri = self.session.http.get(
                self.OEMBED_URL,
                params={"url": self.url},
                schema=self._uri_schema,
            )

            if viewer and uri:
                api_url = self.session.http.get(
                    self.API_URL.format(viewer["apiUrl"], uri["uri"]),
                    headers={"Authorization": "jwt {}".format(viewer["jwt"])},
                    schema=self._config_url_schema,
                )

            if not api_url:
                return
            data = self.session.http.get(api_url, schema=self._config_schema)

        videos = data["request"]["files"]
        streams = []

        for stream_type in ("hls", "dash"):
            if stream_type not in videos:
                continue
            for _, video_data in videos[stream_type]["cdns"].items():
                log.trace("{0!r}".format(video_data))
                url = video_data.get("url")
                if stream_type == "hls":
                    streams.extend(HLSStream.parse_variant_playlist(self.session, url).items())

                elif stream_type == "dash":
                    p = urlparse(url)
                    if p.path.endswith("dash.mpd"):
                        # LIVE
                        url = self.session.http.get(url).json()["url"]
                    elif p.path.endswith("master.json"):
                        # VOD
                        url = url.replace("master.json", "master.mpd")
                    else:
                        log.error("Unsupported DASH path: {0}".format(p.path))
                        continue

                    streams.extend(DASHStream.parse_manifest(self.session, url).items())

        streams.extend(
            (stream["quality"], HTTPStream(self.session, stream["url"]))
            for stream in videos.get("progressive", [])
        )

        if self.session.get_option("mux-subtitles") and data["request"].get("text_tracks"):
            substreams = {
                s["lang"]: HTTPStream(self.session, "https://vimeo.com" + s["url"])
                for s in data["request"]["text_tracks"]
            }
            for quality, stream in streams:
                yield quality, MuxedStream(self.session, stream, subtitles=substreams)
        else:
            yield from streams


__plugin__ = Vimeo
