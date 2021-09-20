import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.plugin.api.utils import itertags
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?watchstadium\.com/live"
))
class Stadium(Plugin):
    _policy_key_re = re.compile(r"""options:\s*\{.+policyKey:\s*"([^"]+)""", re.DOTALL)
    _API_URL = (
        "https://edge.api.brightcove.com/playback/v1/accounts/{data_account}/videos/{data_video_id}"
        "?ad_config_id={data_ad_config_id}"
    )
    _PLAYER_URL = "https://players.brightcove.net/{data_account}/{data_player}_default/index.min.js"

    _streams_schema = validate.Schema(
        {
            "tags": ["live"],
            "sources": [
                {
                    "src": validate.url(scheme="http"),
                    validate.optional("ext_x_version"): str,
                    "type": str,
                }
            ],
        },
        validate.get("sources"),
    )

    def _get_streams(self):
        res = self.session.http.get(self.url)
        for tag in itertags(res.text, "video"):
            if tag.attributes.get("id") == "brightcove_video_player":
                data_video_id = tag.attributes.get("data-video-id")
                data_account = tag.attributes.get("data-account")
                data_ad_config_id = tag.attributes.get("data-ad-config-id")
                data_player = tag.attributes.get("data-player")

                url = self._PLAYER_URL.format(data_account=data_account, data_player=data_player)
                res = self.session.http.get(url)
                policy_key = self._policy_key_re.search(res.text).group(1)

                headers = {
                    "Accept": "application/json;pk={0}".format(policy_key),
                }
                url = self._API_URL.format(
                    data_account=data_account, data_video_id=data_video_id, data_ad_config_id=data_ad_config_id
                )
                res = self.session.http.get(url, headers=headers)
                streams = self.session.http.json(res, schema=self._streams_schema)

                for stream in streams:
                    if stream["type"] == "application/x-mpegURL":
                        for s in HLSStream.parse_variant_playlist(self.session, stream["src"]).items():
                            yield s
                    else:
                        log.warning("Unexpected stream type: '{0}'".format(stream["type"]))


__plugin__ = Stadium
