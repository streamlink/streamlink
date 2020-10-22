import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json, update_scheme

log = logging.getLogger(__name__)


class Sportschau(Plugin):
    _re_url = re.compile(r"https?://(?:\w+\.)*sportschau.de/")

    _re_player = re.compile(r"https?:(//deviceids-medp.wdr.de/ondemand/\S+\.js)")
    _re_json = re.compile(r"\$mediaObject.jsonpHelper.storeAndPlay\(({.+})\);?")

    _schema_player = validate.Schema(
        validate.transform(_re_player.search),
        validate.any(None, validate.Schema(
            validate.get(1),
            validate.transform(lambda url: update_scheme("https:", url))
        ))
    )
    _schema_json = validate.Schema(
        validate.transform(_re_json.match),
        validate.get(1),
        validate.transform(parse_json),
        validate.get("mediaResource"),
        validate.get("dflt"),
        validate.get("videoURL"),
        validate.transform(lambda url: update_scheme("https:", url))
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls._re_url.match(url) is not None

    def _get_streams(self):
        player_js = self.session.http.get(self.url, schema=self._schema_player)
        if not player_js:
            return

        log.debug("Found player js {0}".format(player_js))

        hls_url = self.session.http.get(player_js, schema=self._schema_json)

        yield from HLSStream.parse_variant_playlist(self.session, hls_url).items()


__plugin__ = Sportschau
