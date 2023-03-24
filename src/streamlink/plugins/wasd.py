"""
$description Russian live-streaming social platform.
$url wasd.tv
$type live
"""

import logging
import re

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?wasd\.tv/(?P<nickname>[^/]+)/?$",
))
class WASD(Plugin):
    _media_schema = validate.Schema({
        "user_id": int,
        "media_container_online_status": str,
        "media_container_status": str,
        "media_container_streams": [{
            "stream_media": [{
                "media_id": int,
                "media_meta": {
                    "media_url": validate.any(str, None),
                    "media_archive_url": validate.any(str, None),
                },
                "media_status": validate.any("STOPPED", "RUNNING"),
                "media_type": "HLS",
            }],
        }],
    })
    _api_schema = validate.Schema({
        "result":
            validate.any(
                _media_schema,
                validate.all(list,
                             validate.get(0),
                             _media_schema),
                [],
            ),
    }, validate.get("result"))
    _api_nicknames_schema = validate.Schema({
        "result": {
            "channel_id": int,
        },
    }, validate.get("result"), validate.get("channel_id"))

    def _get_streams(self):
        nickname = self.match.group("nickname")
        res = self.session.http.get(f"https://wasd.tv/api/channels/nicknames/{nickname}")
        channel_id = self.session.http.json(res, schema=self._api_nicknames_schema)

        res = self.session.http.get(
            "https://wasd.tv/api/v2/media-containers",
            params={
                "media_container_status": "RUNNING",
                "limit": "1",
                "offset": "0",
                "channel_id": channel_id,
                "media_container_type": "SINGLE,COOP",
            },
        )

        json_res = self.session.http.json(res, schema=self._api_schema)
        log.trace("{0!r}".format(json_res))
        if not json_res:
            raise PluginError("No data returned from URL={0}".format(res.url))

        for stream in json_res["media_container_streams"]:
            log.debug("media_container_status: {0}, media_container_online_status: {1}".format(
                json_res["media_container_status"], json_res["media_container_online_status"]))
            for stream_media in stream["stream_media"]:
                if stream_media["media_status"] == "STOPPED":
                    hls_url = stream_media["media_meta"]["media_archive_url"]
                else:
                    hls_url = stream_media["media_meta"]["media_url"]

                yield from HLSStream.parse_variant_playlist(self.session, hls_url).items()


__plugin__ = WASD
