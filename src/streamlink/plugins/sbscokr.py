"""
$description Live TV channels from SBS, a South Korean public broadcaster.
$url www.sbs.co.kr/live
$type live
$region South Korea
"""

import argparse
import logging
import re

from streamlink.plugin import Plugin, pluginargument, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://www\.sbs\.co\.kr/live/(?P<channel>[^/?]+)",
))
@pluginargument(
    "id",
    help=argparse.SUPPRESS,
)
class SBScokr(Plugin):
    _URL_API_CHANNELS = "https://static.apis.sbs.co.kr/play-api/1.0/onair{virtual}/channels"
    _URL_API_CHANNEL = "https://apis.sbs.co.kr/play-api/1.0/onair{virtual}/channel/{channel}"

    def _get_streams(self):
        channel = self.match["channel"]

        for virtual in ("", "/virtual"):
            channels = self.session.http.get(
                self._URL_API_CHANNELS.format(virtual=virtual),
                schema=validate.Schema(
                    validate.parse_json(),
                    {
                        "list": [{
                            "channelid": str,
                        }],
                    },
                    validate.get("list"),
                    validate.map(lambda item: item["channelid"]),
                ),
            )
            if channel in channels:
                break
        else:
            return

        info, hls_url = self.session.http.get(
            self._URL_API_CHANNEL.format(virtual=virtual, channel=channel),
            params={
                "v_type": "2",
                "platform": "pcweb",
                "protocol": "hls",
                "jwt-token": "",
                "ssl": "Y",
                "rscuse": "",
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "onair": {
                        "info": {
                            "channelid": str,
                            "channelname": str,
                            "title": str,
                            "onair_yn": str,
                            "overseas_yn": str,
                            "overseas_text": str,
                        },
                        "source": {
                            "mediasource": {
                                validate.optional("mediaurl"): validate.url(path=validate.endswith(".m3u8")),
                            },
                        },
                    },
                },
                validate.get("onair"),
                validate.union_get(
                    "info",
                    ("source", "mediasource", "mediaurl"),
                ),
            ),
        )

        if info["overseas_yn"] != "Y":
            log.error(f"Geo-restricted content: {info['overseas_text']}")
            return
        if info["onair_yn"] != "Y":
            log.error("This channel is currently unavailable")
            return

        self.id = info["channelid"]
        self.author = info["channelname"]
        self.title = info["title"]

        if hls_url:
            return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = SBScokr
