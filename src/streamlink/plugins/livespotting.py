"""
$url livespotting.tv
$type live
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"""
        (?:
            https?://livespotting\.tv/
            (?:locations\?id=)?
            (?:[^/].+/)?
        )(\w+)
    """, re.VERBOSE
))
class LivespottingTV(Plugin):
    _player_re = re.compile(r"player_id:\s*'(\w+)',\s*livesource_id:\s*'(\w+)'")

    _URL_PLAYER_CONFIG = "https://player.livespotting.com/v1/config/{player_id}.json"
    _URL_PLAYER_SHOWROOM = "https://player.livespotting.com/v2/livesource/{livesource_id}?type=showroom"

    _playlist_schema = validate.Schema({
        "id": validate.text,
        "playlist": validate.url(scheme="http"),
        "playlist_mode": validate.text,
        "weather_live_enable": bool,
    })
    _sources_schema = validate.Schema([{
        validate.optional("mediaid"): validate.text,
        validate.optional("title"): validate.text,
        validate.optional("livestream"): validate.all(validate.url(scheme="http"), validate.contains(".m3u8")),
        "sources": [{"file": validate.all(validate.url(scheme="http"), validate.contains(".m3u8"))}],
    }])
    _livesource_schema = validate.Schema({
        "id": validate.text,
        "source": validate.all(validate.url(scheme="http"), validate.contains(".m3u8")),
    })

    def _get_streams(self):
        source_id = self.match.group(1)
        res = self.session.http.get(self.url)
        m = self._player_re.search(res.text)
        if m:
            _player_id, _source_id = m.groups()
            if _source_id == source_id:
                config_url = self._URL_PLAYER_CONFIG.format(player_id=_player_id)
                log.debug("config_url: {0}".format(config_url))
                res = self.session.http.get(config_url)
                res = self.session.http.json(res, schema=self._playlist_schema)
                log.debug("playlist_mode: {0}".format(res["playlist_mode"]))
                log.debug("weather_live_enable: {0}".format(res["weather_live_enable"]))
                if res["playlist_mode"] == "showroom":
                    playlist_url = self._URL_PLAYER_SHOWROOM.format(livesource_id=_source_id)
                    _schema = self._livesource_schema
                else:
                    playlist_url = res["playlist"]
                    _schema = self._sources_schema

                log.debug("playlist_url: {0}".format(playlist_url))
                res = self.session.http.get(playlist_url)
                res = self.session.http.json(res, schema=_schema)
                log.trace("sources: {0!r}".format(res))
                for source in res if isinstance(res, list) else [res]:
                    _id = source.get("mediaid") or _source_id
                    if _id == _source_id:
                        title = source.get("title", "N/A")
                        log.debug("title: {0}".format(title))
                        if source.get("livestream"):
                            for s in HLSStream.parse_variant_playlist(self.session, source["livestream"]).items():
                                yield s
                        else:
                            log.debug("No 'livestream' source found, trying alt. sources")
                            sources = source.get("sources") or [{"file": source["source"]}]
                            for file in sources:
                                for s in HLSStream.parse_variant_playlist(self.session, file["file"]).items():
                                    yield s


__plugin__ = LivespottingTV
