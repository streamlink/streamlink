import re

from streamlink.compat import html_unescape
from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import DASHStream, HLSStream, HTTPStream
from streamlink.utils import parse_json


class Vimeo(Plugin):
    _url_re = re.compile(r"https?://(player\.vimeo\.com/video/\d+|(www\.)?vimeo\.com/.+)")
    _config_url_re = re.compile(r'(?:"config_url"|\bdata-config-url)\s*[:=]\s*(".+?")')
    _config_re = re.compile(r"var\s+config\s*=\s*({.+?})\s*;")
    _config_url_schema = validate.Schema(
        validate.transform(_config_url_re.search),
        validate.any(
            None,
            validate.Schema(
                validate.get(1),
                validate.transform(parse_json),
                validate.transform(html_unescape),
                validate.url(),
            ),
        ),
    )
    _config_schema = validate.Schema(
        validate.transform(parse_json),
        {
            "request": {
                "files": {
                    validate.optional("dash"): {"cdns": {validate.text: {"url": validate.url()}}},
                    validate.optional("hls"): {"cdns": {validate.text: {"url": validate.url()}}},
                    validate.optional("progressive"): validate.all(
                        [{"url": validate.url(), "quality": validate.text}]
                    ),
                }
            }
        },
    )
    _player_schema = validate.Schema(
        validate.transform(_config_re.search),
        validate.any(None, validate.Schema(validate.get(1), _config_schema)),
    )

    @classmethod
    def can_handle_url(cls, url):
        return Vimeo._url_re.match(url)

    def _get_streams(self):
        if "player.vimeo.com" in self.url:
            data = self.session.http.get(self.url, schema=self._player_schema)
        else:
            api_url = self.session.http.get(self.url, schema=self._config_url_schema)
            if not api_url:
                return
            data = self.session.http.get(api_url, schema=self._config_schema)

        videos = data["request"]["files"]

        for stream_type in ("hls", "dash"):
            if not stream_type in videos:
                continue
            for _, video_data in videos[stream_type]["cdns"].items():
                url = video_data.get("url")
                if stream_type == "hls":
                    for stream in HLSStream.parse_variant_playlist(self.session, url).items():
                        yield stream
                elif stream_type == "dash":
                    url = url.replace("master.json", "master.mpd")
                    for stream in DASHStream.parse_manifest(self.session, url).items():
                        yield stream

        for stream in videos.get("progressive", []):
            yield stream["quality"], HTTPStream(self.session, stream["url"])


__plugin__ = Vimeo
