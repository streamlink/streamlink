import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json
from streamlink.utils.url import update_scheme

log = logging.getLogger(__name__)


class Mico(Plugin):
    author = None
    category = None
    title = None

    url_re = re.compile(r'https?://(?:www\.)?micous\.com/live/\d+')
    json_data_re = re.compile(r'win._profile\s*=\s*({.*})')

    _json_data_schema = validate.Schema(
        validate.transform(json_data_re.search),
        validate.any(None, validate.all(
            validate.get(1),
            validate.transform(parse_json),
            validate.any(None, validate.all({
                'mico_id': int,
                'nickname': validate.text,
                'h5_url': validate.all(
                    validate.transform(lambda x: update_scheme('http:', x)),
                    validate.url(),
                ),
                'is_live': bool,
            })),
        )),
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def get_author(self):
        if self.author is not None:
            return self.author

    def get_category(self):
        if self.category is not None:
            return self.category

    def get_title(self):
        if self.title is not None:
            return self.title

    def _get_streams(self):
        json_data = self.session.http.get(self.url, schema=self._json_data_schema)

        if not json_data:
            log.error('Failed to get JSON data')
            return

        if not json_data['is_live']:
            log.info('This stream is no longer online')
            return

        self.author = json_data['mico_id']
        self.category = 'Live'
        self.title = json_data['nickname']

        return HLSStream.parse_variant_playlist(self.session, json_data['h5_url'])


__plugin__ = Mico
