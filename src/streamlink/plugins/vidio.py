"""
$description Indonesian & international live TV channels and video on-demand service. OTT service from Vidio.
$url vidio.com
$type live, vod
"""
import logging
import re
from urllib.parse import urlsplit, urlunsplit

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?vidio\.com/",
))
class Vidio(Plugin):
    tokens_url = "https://www.vidio.com/live/{id}/tokens"

    def _get_stream_token(self, stream_id, stream_type):
        log.debug("Getting stream token")
        return self.session.http.post(
            self.tokens_url.format(id=stream_id),
            params={"type": stream_type},
            headers={"Referer": self.url},
            schema=validate.Schema(
                validate.parse_json(),
                {"token": str},
                validate.get("token"),
            ),
        )

    def _get_streams(self):
        stream_id, has_token, hls_url, dash_url = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_find(".//*[@data-video-id]"),
                validate.union((
                    validate.get("data-video-id"),
                    validate.all(
                        validate.get("data-video-has-token"),
                        validate.transform(lambda val: val and val != "false"),
                    ),
                    validate.get("data-vjs-clip-hls-url"),
                    validate.get("data-vjs-clip-dash-url"),
                )),
            ),
        )

        if dash_url and has_token:
            token = self._get_stream_token(stream_id, "dash")
            parsed = urlsplit(dash_url)
            dash_url = urlunsplit(parsed._replace(path=f"{token}{parsed.path}"))
            return DASHStream.parse_manifest(
                self.session,
                dash_url,
                headers={"Referer": "https://www.vidio.com/"},
            )

        if not hls_url:
            return

        if has_token:
            token = self._get_stream_token(stream_id, "hls")
            hls_url = f"{hls_url}?{token}"

        return HLSStream.parse_variant_playlist(
            self.session,
            hls_url,
            headers={"Referer": "https://www.vidio.com/"},
        )


__plugin__ = Vidio
