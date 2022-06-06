"""
$description Global live-streaming and video hosting social platform.
$url vimeo.com
$type live, vod
$notes Password protected streams are not supported
"""

import logging
import re
from html import unescape as html_unescape
from time import time
from urllib.parse import urlparse

from streamlink.exceptions import StreamError
from streamlink.plugin import Plugin, PluginArgument, PluginArguments, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.ffmpegmux import MuxedStream
from streamlink.stream.hls import HLSStream, MuxedHLSStream
from streamlink.stream.http import HTTPStream

log = logging.getLogger(__name__)


class VimeoMuxedHLSStream(MuxedHLSStream):
    def __init__(self, session, video, audio, **args):
        super().__init__(session, video, audio, hlsstream=VimeoHLSStream, **args)


class VimeoHLSStream(HLSStream):
    __muxed__ = VimeoMuxedHLSStream

    def __init__(self, session_, url, **args):
        self.session = session_
        self._url = url
        self.api: VimeoAPI = args.pop("api")
        self._parsed_url = urlparse(url)
        self._path_parts = self._parsed_url.path.split("/")
        self._need_update = False
        try:
            self.api.set_expiry_time(self._path_parts[1])
        except ValueError as err:
            raise PluginError(err)
        super().__init__(session_, url, **args)

    @property
    def url(self):
        if self._need_update and not self.api.updating:
            try:
                self.api.set_expiry_time(self.api.auth_data)
            except ValueError as err:
                raise StreamError(err)
            self._path_parts[1] = self.api.auth_data
            self._url = self._parsed_url._replace(path="/".join(self._path_parts)).geturl()
            log.debug("Reloaded Vimeo HLS URL")
            self._need_update = False

        time_now = time()
        if time_now > self.api.expiry_time:
            if not self.api.updating and time_now >= self.api.last_updated + self.api.EXPIRY_TIME_LIMIT:
                log.debug("Reloading Vimeo auth data")
                self.api.reload_auth_data(self._path_parts[1])
            self._need_update = True

        return self._url


class VimeoAPI:
    EXPIRY_TIME_LIMIT = 60

    _expiry_re1 = re.compile(r"^exp=(\d+)~")
    _expiry_re2 = re.compile(r"^(\d+)-")

    def __init__(self, session, url):
        self.session = session
        self.url = url
        self.auth_data = None
        self.expiry_time = None
        self.last_updated = time()
        self.updating = False

        schema_cdns = {"cdns": {str: {"url": validate.any(None, validate.url())}}}
        self._schema_config = validate.Schema(
            validate.parse_json(),
            {
                "request": {
                    "files": {
                        validate.optional("dash"): schema_cdns,
                        validate.optional("hls"): schema_cdns,
                        validate.optional("progressive"): [{"url": validate.url(), "quality": str}],
                    },
                    validate.optional("text_tracks"): [{"url": str, "lang": str}],
                },
            },
            validate.get("request"),
        )

    def get_player_data(self):
        return self.session.http.get(self.url, schema=validate.Schema(
            validate.transform(re.compile(r"var\s+config\s*=\s*({.+?})\s*;").search),
            validate.any(None, validate.all(
                validate.get(1),
                self._schema_config,
            )),
        ))

    def get_api_url(self):
        return self.session.http.get(self.url, schema=validate.Schema(
            validate.transform(re.compile(r'(?:"config_url"|\bdata-config-url)\s*[:=]\s*(".+?")').search),
            validate.any(None, validate.all(
                validate.get(1),
                validate.parse_json(),
                validate.transform(html_unescape),
                validate.url(),
            )),
        ))

    def get_config_data(self, api_url):
        return self.session.http.get(api_url, schema=self._schema_config)

    def get_data(self):
        if "player.vimeo.com" in self.url:
            return self.get_player_data()

        api_url = self.get_api_url()
        if not api_url:
            return

        return self.get_config_data(api_url)

    def set_expiry_time(self, path):
        m = self._expiry_re1.search(path) or self._expiry_re2.search(path)
        if not m:
            raise ValueError("expiry value not found in URL")
        self.expiry_time = int(m.group(1)) - self.EXPIRY_TIME_LIMIT

    def reload_auth_data(self, auth_part):
        self.updating = True
        self.last_updated = time()

        data = self.get_data()
        if not data:
            raise StreamError("No video data found")

        videos = data["files"]
        if "hls" not in videos:
            raise StreamError("HLS key not found in video data")

        for video_data in videos["hls"]["cdns"].values():
            url: str = video_data.get("url")
            if not url:
                continue
            res = self.session.http.get(url)
            if res.history:
                url = res.url

            parsed_url = urlparse(url)
            path_parts = parsed_url.path.split("/")
            if (
                self._expiry_re1.search(path_parts[1]) and self._expiry_re1.search(auth_part)
                or self._expiry_re2.search(path_parts[1]) and self._expiry_re2.search(auth_part)
            ):
                self.auth_data = path_parts[1]
                break
        else:
            raise StreamError("Failed to get new auth data from URL")

        self.updating = False


@pluginmatcher(re.compile(
    r"https?://(player\.vimeo\.com/video/\d+|(www\.)?vimeo\.com/.+)"
))
class Vimeo(Plugin):
    arguments = PluginArguments(
        PluginArgument("mux-subtitles", is_global=True)
    )

    def _get_streams(self):
        api = VimeoAPI(self.session, self.url)
        data = api.get_data()
        if not data:
            return

        videos = data["files"]
        streams = []

        for stream_type in ("hls", "dash"):
            if stream_type not in videos:
                continue
            for video_data in videos[stream_type]["cdns"].values():
                log.trace(f"{video_data!r}")
                url = video_data.get("url")
                if not url:
                    log.error("This video requires a logged-in session to view it")
                    return

                if stream_type == "hls":
                    for stream in VimeoHLSStream.parse_variant_playlist(self.session, url, api=api).items():
                        streams.append(stream)
                elif stream_type == "dash":
                    p = urlparse(url)
                    if p.path.endswith("dash.mpd"):
                        # LIVE
                        url = self.session.http.get(url, schema=validate.Schema(
                            validate.parse_json(),
                            {"url": validate.url()},
                            validate.get("url"),
                        ))
                    elif p.path.endswith("master.json"):
                        # VOD
                        url = url.replace("master.json", "master.mpd")
                    else:
                        log.error(f"Unsupported DASH path: {p.path}")
                        continue

                    for stream in DASHStream.parse_manifest(self.session, url).items():
                        streams.append(stream)

        for stream in videos.get("progressive", []):
            streams.append((stream["quality"], HTTPStream(self.session, stream["url"])))

        if self.get_option("mux_subtitles") and data.get("text_tracks"):
            substreams = {}
            for text_track in data.get("text_tracks"):
                text_lang: str = text_track["lang"]
                text_url: str = text_track["url"]
                text_url = urlparse(text_url)._replace(scheme="https", netloc="vimeo.com").geturl()
                substreams[text_lang] = HTTPStream(self.session, text_url)
            for quality, stream in streams:
                yield quality, MuxedStream(self.session, stream, subtitles=substreams)
        else:
            yield from streams


__plugin__ = Vimeo
