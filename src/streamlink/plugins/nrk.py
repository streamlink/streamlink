"""
$description Live TV channels and video on-demand service from NRK, a Norwegian public, state-owned broadcaster.
$url tv.nrk.no
$url radio.nrk.no
$type live, vod
$region Norway
"""

import logging
import re
from urllib.parse import urljoin

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:tv|radio)\.nrk\.no/(program|direkte|serie|podkast)(?:/.+)?/([^/]+)",
))
class NRK(Plugin):
    _psapi_url = "https://psapi.nrk.no"
    # Program type to manifest type mapping
    _program_type_map = {
        "direkte": "channel",
        "serie": "program",
        "program": "program",
        "podkast": "podcast",
    }

    _program_id_re = re.compile(r'<meta property="nrk:program-id" content="([^"]+)"')

    _playable_schema = validate.Schema(validate.any(
        {
            "playable": {
                "assets": [{
                    "url": validate.url(),
                    "format": str,
                }],
            },
            "statistics": {
                validate.optional("luna"): validate.any(None, {
                    "data": {
                        "title": str,
                        "category": validate.any(None, str),
                    },
                }),
            },
        },
        {
            "nonPlayable": {
                "reason": str,
            },
        },
    ))

    def _get_streams(self):
        # Construct manifest URL for this program.
        program_type, program_id = self.match.groups()
        manifest_type = self._program_type_map.get(program_type)
        if manifest_type is None:
            log.error(f"Unknown program type '{program_type}'")
            return None

        # Fetch program_id.
        res = self.session.http.get(self.url)
        m = self._program_id_re.search(res.text)
        if m is not None:
            program_id = m.group(1)
        elif program_id is None:
            log.error("Could not extract program ID from URL")
            return None

        manifest_url = urljoin(self._psapi_url, f"playback/manifest/{manifest_type}/{program_id}")

        # Extract media URL.
        res = self.session.http.get(manifest_url)
        manifest = self.session.http.json(res, schema=self._playable_schema)
        if "nonPlayable" in manifest:
            reason = manifest["nonPlayable"]["reason"]
            log.error(f"Not playable ({reason})")
            return None
        self._set_metadata(manifest)
        asset = manifest["playable"]["assets"][0]

        # Some streams such as podcasts are not HLS but plain files.
        if asset["format"] == "HLS":
            return HLSStream.parse_variant_playlist(self.session, asset["url"])
        else:
            return [("live", HTTPStream(self.session, asset["url"]))]

    def _set_metadata(self, manifest):
        luna = manifest.get("statistics").get("luna")
        if not luna:
            return
        data = luna["data"]
        self.category = data.get("category")
        self.title = data.get("title")


__plugin__ = NRK
