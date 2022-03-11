"""
$description Live TV channels from CT, a Czech public, state-owned broadcaster.
$url ceskatelevize.cz
$type live
$region Czechia
"""

import logging
import re

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https://(?:www\.)?ceskatelevize\.cz/zive/\w+"
))
class Ceskatelevize(Plugin):
    _re_playlist_info = re.compile(r"{\"type\":\"([a-z]+)\",\"id\":\"([0-9]+)\"")

    def _get_streams(self):
        self.session.http.headers.update({"Referer": self.url})
        schema_data = validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string(".//script[@id='__NEXT_DATA__'][text()]/text()"),
            str,
            validate.parse_json(),
            {
                "props": {
                    "pageProps": {
                        "data": {
                            "liveBroadcast": {
                                # "id": str,
                                "current": validate.any(None, {
                                    "channel": str,
                                    "channelName": str,
                                    "legacyEncoder": str,
                                }),
                                "next": validate.any(None, {
                                    "channel": str,
                                    "channelName": str,
                                    "legacyEncoder": str,
                                })
                            }
                        }
                    }
                }
            },
            validate.get(("props", "pageProps", "data", "liveBroadcast")),
            validate.union_get("current", "next"),
        )

        try:
            data_current, data_next = self.session.http.get(
                self.url, schema=schema_data)
        except PluginError:
            return

        log.debug(f"current={data_current!r}")
        log.debug(f"next={data_next!r}")

        data = data_current or data_next
        video_id = data["legacyEncoder"]
        self.title = data["channelName"]

        _hash = self.session.http.get(
            "https://www.ceskatelevize.cz/v-api/iframe-hash/",
            schema=validate.Schema(str))
        res = self.session.http.get(
            "https://www.ceskatelevize.cz/ivysilani/embed/iFramePlayer.php",
            params={
                "hash": _hash,
                "origin": "iVysilani",
                "autoStart": "true",
                "videoID": video_id,
            },
        )

        m = self._re_playlist_info.search(res.text)
        if not m:
            return
        _type, _id = m.groups()

        data = self.session.http.post(
            "https://www.ceskatelevize.cz/ivysilani/ajax/get-client-playlist/",
            data={
                "playlist[0][type]": _type,
                "playlist[0][id]": _id,
                "requestUrl": "/ivysilani/embed/iFramePlayer.php",
                "requestSource": "iVysilani",
                "type": "html",
                "canPlayDRM": "false",
            },
            headers={
                "x-addr": "127.0.0.1",
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    validate.optional("streamingProtocol"): str,
                    "url": validate.any(
                        validate.url(),
                        "Error",
                        "error_region"
                    )
                }
            ),
        )

        if data["url"] in ["Error", "error_region"]:
            log.error("This stream is not available")
            return

        url = self.session.http.get(
            data["url"],
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "playlist": [{
                        validate.optional("type"): str,
                        "streamUrls": {
                            "main": validate.url(),
                        }
                    }]
                },
                validate.get(("playlist", 0, "streamUrls", "main"))
            )
        )
        return DASHStream.parse_manifest(self.session, url)


__plugin__ = Ceskatelevize
