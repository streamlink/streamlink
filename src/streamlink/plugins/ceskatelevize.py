"""
Plugin for Czech TV (Ceska televize).

Following channels are working:
    * CT1 - https://www.ceskatelevize.cz/porady/ct1/
    * CT2 - https://www.ceskatelevize.cz/porady/ct2/
    * CT24 - https://ct24.ceskatelevize.cz/#live
    * CT sport - https://www.ceskatelevize.cz/sport/zive-vysilani/
    * CT Decko - https://decko.ceskatelevize.cz/zive
    * CT Art - https://www.ceskatelevize.cz/porady/art/

Additionally, videos from iVysilani archive should work as well.
"""
import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents, validate
from streamlink.stream import HLSStream
from streamlink.exceptions import PluginError

_url_re = re.compile(
    r'http(s)?://([^.]*.)?ceskatelevize.cz'
)
_player_re = re.compile(
    r'ivysilani/embed/iFramePlayer[^"]+'
)
_hash_re = re.compile(
    r'hash:"([0-9a-z]+)"'
)
_playlist_info_re = re.compile(
    r'{"type":"([a-z]+)","id":"([0-9]+)"'
)
_playlist_url_schema = validate.Schema({
    validate.optional("streamingProtocol"): validate.text,
    "url": validate.any(
        validate.url(),
        "Error",
        "error_region"
    )
})
_playlist_schema = validate.Schema({
    "playlist": [{
        validate.optional("type"): validate.text,
        "streamUrls": {
            "main": validate.url(),
        }
    }]
})

log = logging.getLogger(__name__)


def _find_playlist_info(response):
    """
    Finds playlist info (type, id) in HTTP response.

    :param response: Response object.
    :returns: Dictionary with type and id.
    """
    values = {}
    matches = _playlist_info_re.search(response.text)
    if matches:
        values['type'] = matches.group(1)
        values['id'] = matches.group(2)

    return values


def _find_player_url(response):
    """
    Finds embedded player url in HTTP response.

    :param response: Response object.
    :returns: Player url (str).
    """
    url = ''
    matches = _player_re.search(response.text)
    if matches:
        tmp_url = matches.group(0).replace('&amp;', '&')
        if 'hash' not in tmp_url:
            # there's no hash in the URL, try to find it
            matches = _hash_re.search(response.text)
            if matches:
                url = tmp_url + '&hash=' + matches.group(1)
        else:
            url = tmp_url

    return 'http://ceskatelevize.cz/' + url


class Ceskatelevize(Plugin):

    ajax_url = 'https://www.ceskatelevize.cz/ivysilani/ajax/get-client-playlist'

    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        self.session.http.headers.update({'User-Agent': useragents.IPAD})
        self.session.http.verify = False
        log.warning('SSL certificate verification is disabled.')
        # fetch requested url and find playlist info
        response = self.session.http.get(self.url)
        info = _find_playlist_info(response)

        if not info:
            # playlist info not found, let's try to find player url
            player_url = _find_player_url(response)
            if not player_url:
                raise PluginError('Cannot find playlist info or player url!')

            # get player url and try to find playlist info in it
            response = self.session.http.get(player_url)
            info = _find_playlist_info(response)
            if not info:
                raise PluginError('Cannot find playlist info in the player url!')

        log.trace('{0!r}'.format(info))

        data = {
            'playlist[0][type]': info['type'],
            'playlist[0][id]': info['id'],
            'requestUrl': '/ivysilani/embed/iFramePlayer.php',
            'requestSource': 'iVysilani',
            'type': 'html'
        }
        headers = {
            'x-addr': '127.0.0.1',
        }

        # fetch playlist url
        response = self.session.http.post(
            self.ajax_url,
            data=data,
            headers=headers
        )
        json_data = self.session.http.json(response, schema=_playlist_url_schema)
        log.trace('{0!r}'.format(json_data))

        if json_data['url'] in ['Error', 'error_region']:
            log.error('This stream is not available')
            return

        # fetch playlist
        response = self.session.http.post(json_data['url'])
        json_data = self.session.http.json(response, schema=_playlist_schema)
        log.trace('{0!r}'.format(json_data))
        playlist = json_data['playlist'][0]['streamUrls']['main']
        return HLSStream.parse_variant_playlist(self.session, playlist)


__plugin__ = Ceskatelevize
