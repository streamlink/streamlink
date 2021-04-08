import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class LivespottingTV(Plugin):
    _url_re = re.compile(r"https?://livespotting\.tv/locations\?id=(\w+)")
    _player_re = re.compile(r"player_id:\s*'(\w+)',\s*livesource_id:\s*'(\w+)'")

    _URL_PLAYER_CONFIG = "https://player.livespotting.com/v1/config/{player_id}.json"

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

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def get_title(self):
        return self.title

    def _get_streams(self):
        source_id = self._url_re.search(self.url).group(1)
        res = self.session.http.get(self.url)
        m = self._player_re.search(res.text)
        if m:
            _player_id, _source_id = m.groups()
            if _source_id == source_id:
                config_url = self._URL_PLAYER_CONFIG.format(player_id=_player_id)
                res = self.session.http.get(config_url)
                res = self.session.http.json(res, schema=self._playlist_schema)
                log.debug("playlist_mode: {0}".format(res["playlist_mode"]))
                log.debug("weather_live_enable: {0}".format(res["weather_live_enable"]))
                playlist_url = res["playlist"]
                res = self.session.http.get(playlist_url)
                res = self.session.http.json(res, schema=self._sources_schema)
                for source in res:
                    if source.get("mediaid") and source["mediaid"] == _source_id:
                        self.title = source.get("title", "N/A")
                        log.info("Title: {0}".format(self.title))
                        if source.get("livestream"):
                            for s in HLSStream.parse_variant_playlist(self.session, source["livestream"]).items():
                                yield s
                        else:
                            log.debug("No 'livestream' source found, trying alt. sources")
                            for file in source.get("sources", []):
                                for s in HLSStream.parse_variant_playlist(self.session, file["file"]).items():
                                    yield s


__plugin__ = LivespottingTV
