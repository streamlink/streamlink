"""
$description Indonesian & international live TV channels and video on-demand service. OTT service from Vidio.
$url vidio.com
$type live, vod
$metadata id
$metadata title
"""

import logging
import re
from uuid import uuid4

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(r"https?://(?:www\.)?vidio\.com/.+"),
)
class Vidio(Plugin):
    tokens_url = "https://www.vidio.com/live/{id}/tokens"

    def _get_stream_token(self, stream_id, stream_type):
        return self.session.http.post(
            self.tokens_url.format(id=stream_id),
            params={"type": stream_type},
            headers={"Referer": self.url},
            cookies={
                "ahoy_visit": str(uuid4()),
                "ahoy_visitor": str(uuid4()),
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "token": str,
                    "hls_url": validate.any("", validate.url()),
                    "dash_url": validate.any("", validate.url()),
                },
                validate.union_get(
                    "token",
                    "hls_url",
                    "dash_url",
                ),
            ),
        )

    def _get_stream_data(self):
        return self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_find(".//*[@data-video-id]"),
                validate.union((
                    validate.get("data-video-id"),
                    validate.get("data-video-title"),
                    validate.all(
                        validate.get("data-video-has-token"),
                        validate.transform(lambda val: val and val != "false"),
                    ),
                    validate.get("data-vjs-clip-hls-url"),
                    validate.get("data-vjs-clip-dash-url"),
                )),
            ),
        )

    def _get_streams(self):
        self.session.http.headers.update({
            "Origin": "https://www.vidio.com/",
            "Referer": self.url,
        })

        self.id, self.title, has_token, hls_url, dash_url = self._get_stream_data()
        log.debug(f"{self.id=} {has_token=}")

        params = {}
        if has_token:
            token, hls_url, dash_url = self._get_stream_token(self.id, "dash")
            log.trace(f"{token=}")
            params.update([param.split("=", 1) for param in (token.split("&") if token else [])])

        if hls_url:
            return HLSStream.parse_variant_playlist(self.session, hls_url, params=params)
        if dash_url:
            return DASHStream.parse_manifest(self.session, dash_url, params=params)


__plugin__ = Vidio
