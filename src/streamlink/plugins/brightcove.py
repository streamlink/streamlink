"""
$description Global live-streaming and video on-demand hosting platform.
$url players.brightcove.net
$type live, vod
"""

import logging
import re
from urllib.parse import urlparse

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream
from streamlink.utils.parse import parse_qsd

log = logging.getLogger(__name__)


class BrightcovePlayer:
    URL_PLAYER = "https://players.brightcove.net/{account_id}/{player_id}/index.html?videoId={video_id}"
    URL_API = "https://edge.api.brightcove.com/playback/v1/accounts/{account_id}/videos/{video_id}"

    def __init__(self, session, account_id, player_id="default_default"):
        self.session = session
        self.account_id = account_id
        self.player_id = player_id
        self.title = None
        log.debug(f"Creating player for account {account_id} (player_id={player_id})")

    def get_streams(self, video_id):
        log.debug(f"Finding streams for video: {video_id}")

        player_url = self.URL_PLAYER.format(
            account_id=self.account_id,
            player_id=self.player_id,
            video_id=video_id
        )

        policy_key = self.session.http.get(
            player_url,
            params={"videoId": video_id},
            schema=validate.Schema(
                re.compile(r"""policyKey\s*:\s*(?P<q>['"])(?P<key>[\w-]+)(?P=q)"""),
                validate.any(None, validate.get("key"))
            )
        )
        if not policy_key:
            raise PluginError("Could not find Brightcove policy key")
        log.debug(f"Found policy key: {policy_key}")

        self.session.http.headers.update({"Referer": player_url})
        sources, self.title = self.session.http.get(
            self.URL_API.format(account_id=self.account_id, video_id=video_id),
            headers={"Accept": f"application/json;pk={policy_key}"},
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "sources": [{
                        "src": validate.url(),
                        validate.optional("type"): str,
                        validate.optional("container"): str,
                        validate.optional("height"): int,
                        validate.optional("avg_bitrate"): int,
                    }],
                    validate.optional("name"): str,
                },
                validate.union_get("sources", "name")
            )
        )

        for source in sources:
            if source.get("type") in ("application/vnd.apple.mpegurl", "application/x-mpegURL"):
                yield from HLSStream.parse_variant_playlist(self.session, source.get("src")).items()

            elif source.get("container") == "MP4":
                # determine quality name
                if source.get("height"):
                    q = f"{source.get('height')}p"
                elif source.get("avg_bitrate"):
                    q = f"{source.get('avg_bitrate') // 1000}k"
                else:
                    q = "live"

                yield q, HTTPStream(self.session, source.get("src"))


@pluginmatcher(re.compile(
    r"https?://players\.brightcove\.net/(?P<account_id>[^/]+)/(?P<player_id>[^/]+)/index\.html"
))
class Brightcove(Plugin):
    def _get_streams(self):
        video_id = parse_qsd(urlparse(self.url).query).get("videoId")
        player = BrightcovePlayer(self.session, self.match.group("account_id"), self.match.group("player_id"))
        streams = dict(player.get_streams(video_id))
        self.title = player.title

        return streams


__plugin__ = Brightcove
