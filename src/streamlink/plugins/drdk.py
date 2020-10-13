import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class DRDK(Plugin):
    live_api_url = 'https://www.dr-massive.com/api/page'

    url_re = re.compile(r'''
        https?://(?:www\.)?dr\.dk/drtv
        (/kanal/[\w-]+)
    ''', re.VERBOSE)

    _live_data_schema = validate.Schema(
        {'item': {'customFields': {
            validate.optional('hlsURL'): validate.url(),
            validate.optional('hlsWithSubtitlesURL'): validate.url(),
        }}},
        validate.get('item'),
        validate.get('customFields'),
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

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
        m = self.url_re.match(self.url)
        path = m and m.group(1)
        log.debug("Path={0}".format(path))

        return self._get_live(path)


__plugin__ = DRDK
