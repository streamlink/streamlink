import logging
import re

from streamlink.plugin import Plugin, PluginArguments, PluginArgument
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class DRDK(Plugin):
    live_api_url = (
        'https://www.dr-massive.com/api/page?device=web_browser'
        '&ff=idp,ldp&geoLocation=dk&isDeviceAbroad=false&lang=da'
        '&list_page_size=24&max_list_prefetch=3'
        '&path={0}'
        '&segments=drtv&sub=Anonymous&text_entry_format=html'
    )

    url_re = re.compile(r'''
        https?://(?:www\.)?dr\.dk/drtv
        (/(kanal)/[\w-]+)
    ''', re.VERBOSE)

    _live_data_schema = validate.Schema(
        {'item': {'customFields': {
            'hlsURL': validate.url(),
            'hlsWithSubtitlesURL': validate.url(),
        }}},
        validate.get('item'),
        validate.get('customFields'),
    )

    arguments = PluginArguments(
        PluginArgument(
            'live-subtitles',
            action='store_true',
            help="""
            Enable Danish subtitles for live channels if they are available.
            """,
        ),
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_live(self, path):
        res = self.session.http.get(self.live_api_url.format(path))
        playlists = self.session.http.json(res, schema=self._live_data_schema)

        if self.get_option('live_subtitles'):
            selected_playlist = 'hlsWithSubtitlesURL'
        else:
            selected_playlist = 'hlsURL'

        for playlist_name, playlist_url in playlists.items():
            if selected_playlist == playlist_name:
                log.debug("{0}={1}".format(playlist_name, playlist_url))
                return HLSStream.parse_variant_playlist(
                    self.session,
                    playlist_url,
                )

    def _get_streams(self):
        m = self.url_re.match(self.url)
        path, url_type = m and m.groups()
        log.debug("Path={0}".format(path))
        log.debug("URL type={0}".format(url_type))

        if url_type == 'kanal':
            return self._get_live(path)


__plugin__ = DRDK
