"""
$description Live TV channels and video on-demand service from NOS, a Dutch public, state-owned broadcaster.
$url nos.nl
$type live, vod
$region Netherlands
"""

import logging
import re

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:\w+\.)?nos\.nl/(?:livestream|collectie|video|uitzendingen)",
))
class NOS(Plugin):
    _msg_live_offline = "This livestream is offline."
    vod_keys = {
        "pages/Collection/Video/Video": "item",
        "pages/Video/Video": "video",
    }

    def _get_streams(self):
        try:
            scripts = self.session.http.get(self.url, schema=validate.Schema(
                validate.parse_html(),
                validate.xml_findall(".//script[@type='application/json'][@data-ssr-name]"),
                [
                    validate.union((
                        validate.get("data-ssr-name"),
                        validate.all(
                            validate.getattr("text"),
                            validate.parse_json()
                        )
                    ))
                ]
            ))
        except PluginError:
            log.error("Could not find any stream data")
            return

        for _data_ssr_name, _data_json in scripts:
            video_url = None
            log.trace(f"Found _data_ssr_name={_data_ssr_name}")

            if _data_ssr_name == "pages/Broadcasts/Broadcasts":
                self.title, video_url, is_live = validate.Schema(
                    {"currentLivestream": {
                        "is_live": bool,
                        "title": str,
                        "stream": validate.url(),
                    }},
                    validate.get("currentLivestream"),
                    validate.union_get("title", "stream", "is_live")
                ).validate(_data_json)
                if not is_live:
                    log.error(self._msg_live_offline)
                    continue

            elif _data_ssr_name == "pages/Livestream/Livestream":
                self.title, video_url, is_live = validate.Schema(
                    {
                        "streamIsLive": bool,
                        "title": str,
                        "stream": validate.url(),
                    },
                    validate.union_get("title", "stream", "streamIsLive")
                ).validate(_data_json)
                if not is_live:
                    log.error(self._msg_live_offline)
                    continue

            elif _data_ssr_name in self.vod_keys.keys():
                _key = self.vod_keys[_data_ssr_name]
                self.title, video_url = validate.Schema(
                    {_key: {
                        "title": str,
                        "aspect_ratios": {
                            "profiles": validate.all(
                                [{
                                    "name": str,
                                    "url": validate.url(),
                                }],
                                validate.filter(lambda p: p["name"] == "hls_unencrypted")
                            )
                        }
                    }},
                    validate.get(_key),
                    validate.union_get("title", ("aspect_ratios", "profiles", 0, "url"))
                ).validate(_data_json)

            if video_url is not None:
                return HLSStream.parse_variant_playlist(self.session, video_url)


__plugin__ = NOS
