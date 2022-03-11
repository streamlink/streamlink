"""
$description Live TV channels from DR, a Danish public, state-owned broadcaster.
$url dr.dk
$type live
$region Denmark
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?dr\.dk/drtv(/kanal/[\w-]+)"
))
class DRDK(Plugin):
    live_api_url = 'https://www.dr-massive.com/api/page'

    _live_data_schema = validate.Schema(
        {'item': {'customFields': {
            validate.optional('hlsURL'): validate.url(),
            validate.optional('hlsWithSubtitlesURL'): validate.url(),
        }}},
        validate.get('item'),
        validate.get('customFields'),
    )

    def _get_live(self, path):
        params = dict(
            ff='idp',
            path=path,
        )
        res = self.session.http.get(self.live_api_url, params=params)
        playlists = self.session.http.json(res, schema=self._live_data_schema)

        streams = {}
        for name, url in playlists.items():
            name_prefix = ''
            if name == 'hlsWithSubtitlesURL':
                name_prefix = 'subtitled_'

            streams.update(HLSStream.parse_variant_playlist(
                self.session,
                url,
                name_prefix=name_prefix,
            ))

        return streams

    def _get_streams(self):
        path = self.match.group(1)
        log.debug("Path={0}".format(path))

        return self._get_live(path)


__plugin__ = DRDK
