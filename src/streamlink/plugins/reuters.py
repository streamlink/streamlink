import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.plugin.api.utils import itertags
from streamlink.stream import HLSStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)


class Reuters(Plugin):
    _url_re = re.compile(r'https?://(.*?\.)?reuters\.(com|tv)')
    _id_re = re.compile(r'(/l/|id=)(?P<id>.*?)(/|\?|$)')
    _iframe_url = 'https://www.reuters.tv/l/{0}/?nonav=true'
    _hls_re = re.compile(r'''(?<!')https://[^"';!<>]+\.m3u8''')
    _json_re = re.compile(r'''(?P<data>{.*});''')
    _data_schema = validate.Schema(
        validate.transform(_json_re.search),
        validate.any(
            None,
            validate.all(
                validate.get('data'),
                validate.transform(parse_json),
                {
                    'title': validate.text,
                    'items': [
                        {
                            'title': validate.text,
                            'type': validate.text,
                            'resources': [
                                {
                                    'mimeType': validate.text,
                                    'uri': validate.url(),
                                    validate.optional('protocol'): validate.text,
                                    validate.optional('entityType'): validate.text,
                                }
                            ]
                        }
                    ],
                }
            )
        )
    )

    def __init__(self, url):
        super().__init__(url)
        self.title = None

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def get_title(self):
        if not self.title:
            self._get_data()
        return self.title

    def _get_data(self):
        res = self.session.http.get(self.url)
        for script in itertags(res.text, 'script'):
            if script.attributes.get('type') == 'text/javascript' and '#rtvIframe' in script.text:
                m = self._id_re.search(self.url)
                if m and m.group('id'):
                    log.debug('ID: {0}'.format(m.group('id')))
                    res = self.session.http.get(self._iframe_url.format(m.group('id')))

        for script in itertags(res.text, 'script'):
            if script.attributes.get('type') == 'text/javascript' and 'RTVJson' in script.text:
                data = self._data_schema.validate(script.text)
                if not data:
                    continue
                self.title = data['title']
                for item in data['items']:
                    if data['title'] == item['title']:
                        log.trace('{0!r}'.format(item))
                        log.debug('Type: {0}'.format(item['type']))
                        for res in item['resources']:
                            if res['mimeType'] == 'application/x-mpegURL':
                                return res['uri']

        # fallback
        for title in itertags(res.text, 'title'):
            self.title = title.text
        m = self._hls_re.search(res.text)
        if not m:
            log.error('Unsupported PageType.')
            return
        return m.group(0)

    def _get_streams(self):
        hls_url = self._get_data()
        if not hls_url:
            return
        log.debug('URL={0}'.format(hls_url))
        return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = Reuters
