import re
from urllib.parse import urljoin

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream, HTTPStream

_id_re = re.compile(r"/(program|direkte|serie|podkast)(?:/.+)?/([^/]+)")
_url_re = re.compile(r"https?://(tv|radio).nrk.no/")

_mediaelement_schema = validate.Schema({
    "mediaUrl": validate.url(
        scheme="http",
        path=validate.endswith(".m3u8")
    )
})

_playable_schema = validate.Schema({
    "playable": validate.all(
        {
            "assets": validate.all(
                [{
                    "url": validate.url(
                        scheme="http",
                        path=validate.any(
                            validate.endswith(".m3u8"),
                            validate.endswith(".mp3")
                        ),
                    ),
                    "format": validate.all(validate.text),
                }]
            ),
        }
    ),
    "statistics": {
        "luna": {
            "data": {
                "title": validate.text,
            },
        },
    },
})


class NRK(Plugin):
    _psapi_url = 'https://psapi.nrk.no'

    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams(self):
        # Construct manifest URL for this program.
        program_type, program_id = _id_re.search(self.url).groups()
        if program_type == 'direkte':
            manifest_type = 'channel'
        elif program_type == 'serie':
            manifest_type = 'program'
        elif program_type == 'podkast':
            manifest_type = 'podcast'
        manifest_url = urljoin(self._psapi_url, "playback/manifest/{0}/{1}".format(manifest_type, program_id))

        # Extract media URL.
        res = self.session.http.get(manifest_url)
        manifest = self.session.http.json(res, schema=_playable_schema)
        asset = manifest['playable']['assets'][0]

        # Some streams such as podcasts are not HLS but plain files.
        if asset['format'] == 'HLS':
            return HLSStream.parse_variant_playlist(self.session, asset['url'])
        else:
            return [(self._get_title(manifest), HTTPStream(self.session, asset['url']))]

    def _get_title(self, manifest):
        statistics = manifest.get("statistics")
        if not statistics:
            return None
        luna = statistics.get("luna")
        if not luna:
            return None
        data = luna.get("data")
        if not data:
            return None
        return data.get("title")


__plugin__ = NRK
