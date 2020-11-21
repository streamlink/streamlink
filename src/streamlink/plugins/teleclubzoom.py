import logging
import re
from urllib.parse import urlparse

from streamlink.exceptions import PluginError
from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.plugin.api.utils import itertags
from streamlink.stream import HLSStream
from streamlink.utils import update_scheme

log = logging.getLogger(__name__)


class TeleclubZoom(Plugin):

    _url_re = re.compile(r'https?://(?:www\.)?teleclubzoom\.ch')

    API_URL = 'https://{netloc}/webservice/http/rest/client/live/play/{id}'
    PLAYLIST_URL = 'https://{netloc}/{app}/ngrp:{name}_all/playlist.m3u8'

    _api_schema = validate.Schema(
        {
            'playStreamName': validate.text,
            'cdnHost': validate.text,
            'streamProperties': {
                validate.optional('server'): validate.text,
                validate.optional('name'): validate.text,
                'application': validate.text,
            }
        }
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        iframe_url = None
        page = self.session.http.get(self.url)
        for a in itertags(page.text, 'a'):
            if a.attributes.get('class') == 'play-live':
                iframe_url = update_scheme(self.url, a.attributes['data-url'])
                break

        if not iframe_url:
            raise PluginError('Could not find iframe.')

        parsed = urlparse(iframe_url)
        path_list = parsed.path.split('/')
        if len(path_list) != 6:
            # only support a known iframe url style,
            # the video id might be on a different spot if the url changes
            raise PluginError('unsupported iframe URL: {0}'.format(iframe_url))

        res = self.session.http.get(
            self.API_URL.format(netloc=parsed.netloc, id=path_list[4]))

        data = self.session.http.json(res, schema=self._api_schema)
        log.trace('{0!r}'.format(data))

        url = self.PLAYLIST_URL.format(
            app=data['streamProperties']['application'],
            name=data['playStreamName'],
            netloc=data['cdnHost'],
        )
        return HLSStream.parse_variant_playlist(self.session, url)


__plugin__ = TeleclubZoom
