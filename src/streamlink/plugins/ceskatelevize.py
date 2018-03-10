"""
Plugin for Czech TV (Ceska televize).

Following channels are working:
    * CT1 - http://www.ceskatelevize.cz/ct1/zive/
    * CT2 - http://www.ceskatelevize.cz/ct2/zive/
    * CT24 - http://www.ceskatelevize.cz/ct24/
    * CT sport - http://www.ceskatelevize.cz/sport/zive-vysilani/
    * CT Decko - http://decko.ceskatelevize.cz/zive/
    * CT Art - http://www.ceskatelevize.cz/art/zive/

Additionally, videos from iVysilani archive should work as well.
"""
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
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
    "url": validate.any(
        validate.url(),
        "error_region"
    )
})
_playlist_schema = validate.Schema({
    "playlist": [{
        "streamUrls": {
            "main": validate.url(),
        }
    }]
})


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

    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        # fetch requested url and find playlist info
        response = http.get(self.url)
        info = _find_playlist_info(response)

        if not info:
            # playlist info not found, let's try to find player url
            player_url = _find_player_url(response)
            if not player_url:
                raise PluginError('Cannot find playlist info or player url!')

            # get player url and try to find playlist info in it
            response = http.get(player_url)
            info = _find_playlist_info(response)
            if not info:
                raise PluginError('Cannot find playlist info in the player url!')

        data = {
            'playlist[0][type]': info['type'],
            'playlist[0][id]': info['id'],
            'requestUrl': '/ivysilani/embed/iFramePlayerCT24.php',
            'requestSource': 'iVysilani',
            'type': 'html'
        }
        headers = {
            'x-addr': '127.0.0.1',
        }

        # fetch playlist url
        response = http.post(
            'http://www.ceskatelevize.cz/ivysilani/ajax/get-client-playlist',
            data=data,
            headers=headers
        )
        json_data = http.json(response, schema=_playlist_url_schema)

        if json_data['url'] == "error_region":
            self.logger.error("This stream is not available in your territory")
            return

        # fetch playlist
        response = http.post(json_data['url'])
        json_data = http.json(response, schema=_playlist_schema)
        playlist = json_data['playlist'][0]['streamUrls']['main']
        return HLSStream.parse_variant_playlist(self.session, playlist)


__plugin__ = Ceskatelevize
