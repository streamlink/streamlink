import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.plugin.api.utils import itertags
from streamlink.stream.hls import HLSStream
from streamlink.utils.parse import parse_json

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
        res = self.session.http.get(self.url)
        for script in itertags(res.text, "script"):
            _type = script.attributes.get("type")
            if not (_type and _type == "application/json"):
                continue

            video_url = None
            _data_ssr_name = script.attributes.get("data-ssr-name")
            if not _data_ssr_name:
                continue

            log.trace(f"Found _data_ssr_name={_data_ssr_name}")
            if _data_ssr_name == "pages/Broadcasts/Broadcasts":
                self.title, video_url, is_live = parse_json(script.text, schema=validate.Schema({
                    "currentLivestream": {
                        "is_live": bool,
                        "title": str,
                        "stream": validate.url(),
                    }},
                    validate.get("currentLivestream"),
                    validate.union_get("title", "stream", "is_live")))
                if not is_live:
                    log.error(self._msg_live_offline)
                    continue
            elif _data_ssr_name == "pages/Livestream/Livestream":
                self.title, video_url, is_live = parse_json(script.text, schema=validate.Schema({
                    "streamIsLive": bool,
                    "title": str,
                    "stream": validate.url(),
                }, validate.union_get("title", "stream", "streamIsLive")))
                if not is_live:
                    log.error(self._msg_live_offline)
                    continue
            elif _data_ssr_name in self.vod_keys.keys():
                _key = self.vod_keys[_data_ssr_name]
                self.title, video_url = parse_json(script.text, schema=validate.Schema({
                    _key: {
                        "title": str,
                        "aspect_ratios": {
                            "profiles": validate.all([{
                                "name": str,
                                "url": validate.url(),
                            }], validate.filter(lambda n: n["name"] == "hls_unencrypted"))
                        }
                    }},
                    validate.get(_key),
                    validate.union_get("title", ("aspect_ratios", "profiles", 0, "url"))))

            if video_url is not None:
                yield from HLSStream.parse_variant_playlist(self.session, video_url).items()
                break


__plugin__ = NOS
