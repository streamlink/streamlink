import re

from uuid import uuid4

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream

import logging
log = logging.getLogger(__name__)


class Pluto(Plugin):
    url_re = re.compile(r'https?://(?:www\.)?pluto\.tv/live-tv/(?P<slug>[a-zA-Z0-9-]+)')

    api_url = 'https://api.pluto.tv/v2/channels'

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        slug = self.url_re.match(self.url).groups('slug').lower()

        channels_res = self.session.http.get(self.api_url)
        channels_data = channels_res.json()
        channel_match = next(filter(lambda x: x['slug'] == slug, channels_data), None)

        if not channel_match:
            log.error('Channel %s not found. It may have been removed.' % slug)
            return

        stream_link_no_sid = channel_match['stitched']['urls'][0]['url']
        sid = str(uuid4())
        stream_link = stream_link_no_sid.replace('&sid=', '&sid=' + sid)

        return HLSStream.parse_variant_playlist(self.session, stream_link)


__plugin__ = Pluto
