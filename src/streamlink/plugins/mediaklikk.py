"""
$description Live TV channels from MTVA, a Hungarian public, state-owned broadcaster.
$url mediaklikk.hu
$url m4sport.hu
$type live
$region Hungary
"""

import logging
import re
from urllib.parse import unquote, urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.utils.url import update_scheme


log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(r"https?://(?:www\.)?(?:mediaklikk|m4sport|hirado|petofilive)\.hu/"),
)
class Mediaklikk(Plugin):
    PLAYER_URL = "https://player.mediaklikk.hu/playernew/player.php"

    def _get_streams(self):
        params = self.session.http.get(
            self.url,
            schema=validate.Schema(
                re.compile(
                    r"""
                        mtva_player_manager\.player\s*\(\s*
                            document\.getElementById\(\s*"\w+"\s*\)\s*,\s*
                            (?P<json>{.*?})\s*
                        \)\s*;
                    """,
                    re.VERBOSE | re.DOTALL,
                ),
                validate.none_or_all(
                    validate.get("json"),
                    validate.parse_json(),
                    {
                        "contentId": validate.any(str, int),
                        validate.optional("streamId"): str,
                        validate.optional("idec"): str,
                        validate.optional("token"): str,
                    },
                ),
            ),
        )
        if not params:
            log.error("Could not find player manager data")
            return

        params.update({
            "video": (
                unquote(params.pop("token"))
                if params.get("token") is not None
                else params.pop("streamId")
            ),
            "noflash": "yes",
            "embedded": "0",
        })  # fmt: skip

        url_parsed = urlparse(self.url)
        skip_vods = url_parsed.netloc.endswith("m4sport.hu") and url_parsed.path.startswith("/elo")

        self.session.http.headers.update({"Referer": self.url})
        playlists = self.session.http.get(
            self.PLAYER_URL,
            params=params,
            schema=validate.Schema(
                re.compile(r"pl\.setup\s*\(\s*(?P<json>{.*?})\s*\)\s*;", re.DOTALL),
                validate.none_or_all(
                    validate.get("json"),
                    validate.parse_json(),
                    {
                        "playlist": [
                            {
                                "file": validate.url(),
                                "type": str,
                            },
                        ],
                    },
                    validate.get("playlist"),
                    validate.filter(lambda p: p["type"] == "hls"),
                    validate.filter(lambda p: not skip_vods or "vod" not in p["file"]),
                    validate.map(lambda p: update_scheme("https://", p["file"])),
                ),
            ),
        )

        for url in playlists or []:
            yield from HLSStream.parse_variant_playlist(self.session, url).items()


__plugin__ = Mediaklikk
