import re
from urllib.parse import urljoin

from streamlink.plugin import Plugin, PluginError
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream, HTTPStream


class NRK(Plugin):
    _psapi_url = 'https://psapi.nrk.no'
    # Program type to manifest type mapping
    _program_type_map = {
        'direkte': 'channel',
        'serie': 'program',
        'program': 'program',
        'podkast': 'podcast',
    }

    _url_re = re.compile(r"https?://(?:tv|radio).nrk.no/(program|direkte|serie|podkast)(?:/.+)?/([^/]+)")

    _playable_schema = validate.Schema({
        "playable": validate.any(
            None,
            {
                "assets": [{
                    "url": validate.url(
                        path=validate.any(
                            validate.endswith(".m3u8"),
                            validate.endswith(".mp3")
                        ),
                    ),
                    "format": str,
                }],
            },
        ),
        "nonPlayable": validate.any(
            None,
            {
                "reason": str,
            },
        ),
        "statistics": {
            validate.optional("luna"): validate.any(
                None,
                {
                    "data": {
                        "title": str,
                    },
                },
            ),
        },
    })

    @classmethod
    def can_handle_url(self, url):
        return self._url_re.match(url)

    def _get_streams(self):
        # Construct manifest URL for this program.
        program_type, program_id = self._url_re.search(self.url).groups()
        manifest_type = self._program_type_map.get(program_type)
        if manifest_type is None:
            raise PluginError(f"Unknown program type '{program_type}'")
        manifest_url = urljoin(self._psapi_url, f"playback/manifest/{manifest_type}/{program_id}")

        # Extract media URL.
        res = self.session.http.get(manifest_url)
        manifest = self.session.http.json(res, schema=self._playable_schema)
        playable = manifest['playable']
        if playable is None:
            reason = manifest["nonPlayable"]["reason"]
            raise PluginError(f"Not playable ({reason})")
        asset = manifest['playable']['assets'][0]

        # Some streams such as podcasts are not HLS but plain files.
        if asset['format'] == 'HLS':
            return HLSStream.parse_variant_playlist(self.session, asset['url'])
        else:
            return [(self._get_title(manifest), HTTPStream(self.session, asset['url']))]

    def _get_title(self, manifest):
        luna = manifest.get("statistics").get("luna")
        if not luna:
            return None
        return luna.get("data").get("title")


__plugin__ = NRK
