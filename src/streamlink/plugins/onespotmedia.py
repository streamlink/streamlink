import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class OneSpotmedia(Plugin):
    _re_url = re.compile(r'https?://(?:www\.)?1spotmedia\.com/#!/live-stream/(?P<media_id>[a-zA-Z0-9]+)')
    title = None

    @classmethod
    def can_handle_url(cls, url):
        return cls._re_url.match(url) is not None

    def get_title(self):
        return self.title

    def _get_streams(self):
        media_id = self._re_url.match(self.url).group('media_id')
        res = self.session.http.get('https://www.1spotmedia.com/index.php/api/vod/get_live_streams')
        data = self.session.http.json(
            res,
            schema=validate.Schema(
                [{
                    '_id': str,
                    'title': str,
                    'mediaType': str,
                    'HLSStream': {'url': validate.url()},
                }],
                validate.filter(lambda k: k['_id'].lower() == media_id.lower()),
                validate.get(0),
            )
        )
        log.trace(f'{data!r}')
        if not data:
            return

        self.title = data['title']
        return HLSStream.parse_variant_playlist(self.session, data['HLSStream']['url'])


__plugin__ = OneSpotmedia
