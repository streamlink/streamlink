import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r'https?://www\.tv8\.com\.tr/canli-yayin'
))
class TV8(Plugin):
    _player_schema = validate.Schema(validate.all({
        'servers': {
            validate.optional('manifest'): validate.url(),
            'hlsmanifest': validate.url(),
        }},
        validate.get('servers')))

    API_URL = 'https://static.personamedia.tv/player/config/tv8.json'

    def get_title(self):
        return 'TV8'

    def _get_streams(self):
        res = self.session.http.get(self.API_URL)
        data = self.session.http.json(res, schema=self._player_schema)
        log.debug('{0!r}'.format(data))
        return HLSStream.parse_variant_playlist(self.session, data['hlsmanifest'])


__plugin__ = TV8
