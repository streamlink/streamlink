import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream, HTTPStream
from streamlink.utils import parse_json, update_scheme

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:\w+\.)*sportschau\.de/"
))
class Sportschau(Plugin):
    _re_player = re.compile(r"https?:(//deviceids-medp.wdr.de/ondemand/\S+\.js)")
    _re_json = re.compile(r"\$mediaObject.jsonpHelper.storeAndPlay\(({.+})\);?")

    def _get_streams(self):
        player_js = self.session.http.get(self.url, schema=validate.Schema(
            validate.transform(self._re_player.search),
            validate.any(None, validate.Schema(
                validate.get(1),
                validate.transform(lambda url: update_scheme("https:", url))
            ))
        ))
        if not player_js:
            return

        log.debug(f"Found player js {player_js}")
        data = self.session.http.get(player_js, schema=validate.Schema(
            validate.transform(self._re_json.match),
            validate.get(1),
            validate.transform(parse_json),
            validate.get("mediaResource"),
            validate.get("dflt"),
            {
                validate.optional("audioURL"): validate.url(),
                validate.optional("videoURL"): validate.url()
            }
        ))

        if data.get("videoURL"):
            yield from HLSStream.parse_variant_playlist(self.session, update_scheme("https:", data.get("videoURL"))).items()
        if data.get("audioURL"):
            yield "audio", HTTPStream(self.session, update_scheme("https:", data.get("audioURL")))


__plugin__ = Sportschau
