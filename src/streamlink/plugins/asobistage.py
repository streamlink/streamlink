"""
$description Japanese live-streaming platform owned by Bandai Namco Entertainment Inc.
$url asobistage.asobistore.jp
$type live, vod
$account A Japanese-region account is required.
$notes Tickets are required. Free viewing pages and rental tickets are not supported.
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https://asobistage\.asobistore\.jp/event/(?P<id>\w+/(?P<type>archive|player)/\w+)(?:[?#]|$)",
))
class AsobiStage(Plugin):
    _URL_CHANNEL_LIST = "{cdn_endpoint}/events/{event_id}/{video_type_id}.json"
    _URL_TOKEN = "https://asobistage-api.asobistore.jp/api/v1/vspf/token"
    _URL_ARCHIVE_M3U8 = "https://survapi.channel.or.jp/proxy/v1/contents/{channel_id}/get_by_cuid"
    _URL_PLAYER_M3U8 = "https://survapi.channel.or.jp/ex/events/{channel_id}"

    def _get_streams(self):
        self.id = self.match.group("id")
        video_type_name = self.match.group("type")

        video_type_id = {
            "archive": "archives",
            "player": "broadcasts",
        }.get(video_type_name) or None
        if not video_type_id:
            log.error(f"Unknown video type: {video_type_name}")
            return

        event_info, cdn_endpoint = self.session.http.get(self.url, schema=validate.Schema(
            validate.union((
                validate.all(
                    validate.parse_html(),
                    validate.xml_xpath_string(".//script[@id='__NEXT_DATA__'][text()]/text()"),
                    validate.parse_json(),
                    {
                        "query": {
                            "event": str,
                            "player_slug": str,
                        },
                        "props": {
                            "pageProps": {
                                "eventCMSData": {
                                    "event_name": str,
                                },
                            },
                        },
                    },
                    validate.transform(lambda obj: {
                        "event_id": obj["query"]["event"],
                        "slug": obj["query"]["player_slug"],
                        "title": obj["props"]["pageProps"]["eventCMSData"]["event_name"],
                    }),
                ),
                validate.all(
                    re.compile(r'"(?P<url>https://asobistage\.asobistore\.jp/cdn/[^/]+)/'),
                    validate.none_or_all(
                        validate.get("url"),
                    ),
                ),
            )),
        ))

        if not cdn_endpoint:
            log.error("Unable to find CDN endpoint.")
            return

        self.title = event_info["title"]

        channel_list_url = self._URL_CHANNEL_LIST.format(
            cdn_endpoint=cdn_endpoint,
            event_id=event_info["event_id"],
            video_type_id=video_type_id,
        )
        channel_ids = self.session.http.get(channel_list_url, schema=validate.Schema(
            validate.parse_json(),
            {
                video_type_id: validate.all(
                    [{
                        "broadcast_slug": str,
                        "channels": validate.all(
                            [{
                                "chennel_vspf_id": str,
                            }],
                            validate.filter(lambda channel: channel["chennel_vspf_id"] != "00000"),
                            validate.map(lambda channel: channel["chennel_vspf_id"]),
                        ),
                    }],
                    validate.filter(lambda broadcast: broadcast["broadcast_slug"] == event_info["slug"]),
                    validate.map(lambda broadcast: broadcast["channels"]),
                ),
            },
            validate.get(video_type_id),
            validate.length(1, op="le"),
            validate.get(0),
        ))
        if not channel_ids:
            log.error("No valid channel found.")
            return

        token = self.session.http.get(self._URL_TOKEN, schema=validate.Schema(
            re.compile(r"\"(?P<token>.+)\""),
            validate.none_or_all(
                validate.get("token"),
            ),
        ))
        if not token:
            log.error("Unable to get token.")
            return

        for channel_id in channel_ids:
            if video_type_name == "archive":
                m3u8_url = self.session.http.get(
                    self._URL_ARCHIVE_M3U8.format(channel_id=channel_id),
                    headers={"Authorization": f"Bearer {token}"},
                    schema=validate.Schema(
                        validate.parse_json(),
                        {
                            "ex_content": {
                                "streaming_url": validate.url(),
                            },
                        },
                        validate.get(("ex_content", "streaming_url")),
                    ),
                )
            elif video_type_name == "player":
                m3u8_url = self.session.http.get(
                    self._URL_PLAYER_M3U8.format(channel_id=channel_id),
                    headers={"Authorization": f"Bearer {token}"},
                    params={"embed": "channel"},
                    schema=validate.Schema(
                        validate.parse_json(),
                        {
                            "data": {
                                "Channel": {
                                    "Custom_live_url": validate.url(),
                                },
                            },
                        },
                        validate.get(("data", "Channel", "Custom_live_url")),
                    ),
                )
            else:
                log.error(f"Unknown video type: {video_type_name}")
                return

            yield from HLSStream.parse_variant_playlist(self.session, m3u8_url).items()


__plugin__ = AsobiStage
