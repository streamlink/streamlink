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
import json
import logging
import re
from html import unescape as html_unescape
from urllib.parse import quote

from streamlink.exceptions import PluginError
from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents, validate
from streamlink.stream import DASHStream, HLSStream

log = logging.getLogger(__name__)


class Ceskatelevize(Plugin):

    ajax_url = 'https://www.ceskatelevize.cz/ivysilani/ajax/get-client-playlist'
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

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    def _get_streams(self):
        self.session.http.headers.update({'User-Agent': useragents.IPAD})
        self.session.http.verify = False
        log.warning('SSL certificate verification is disabled.')
        # fetch requested url and find playlist info
        response = self.session.http.get(self.url)
        info = self._find_playlist_info(response)

        if not info:
            # do next try with new API
            def _fallback_api(*args, **kwargs):
                self.api2 = CeskatelevizeAPI2(self.session, self.url, *args, **kwargs)
                return self.api2._get_streams()

            # playlist info not found, let's try to find player url
            player_url = self._find_player_url(response)
            if not player_url:
                log.debug('Cannot find playlist info or player url, do next try with new API')
                return _fallback_api(res=response)

            # get player url and try to find playlist info in it
            response = self.session.http.get(player_url)
            info = self._find_playlist_info(response)
            if not info:
                log.debug('Cannot find playlist info in the player url, do next try with new API')
                return _fallback_api()

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
        json_data = self.session.http.json(response, schema=self._playlist_url_schema)
        log.trace('{0!r}'.format(json_data))

        if json_data['url'] in ['Error', 'error_region']:
            log.error('This stream is not available')
            return

        # fetch playlist
        response = self.session.http.post(json_data['url'])
        json_data = self.session.http.json(response, schema=self._playlist_schema)
        log.trace('{0!r}'.format(json_data))
        playlist = json_data['playlist'][0]['streamUrls']['main']
        return HLSStream.parse_variant_playlist(self.session, playlist)

    @classmethod
    def _find_playlist_info(cls, response):
        """
        Finds playlist info (type, id) in HTTP response.

        :param response: Response object.
        :returns: Dictionary with type and id.
        """
        values = {}
        matches = cls._playlist_info_re.search(response.text)
        if matches:
            values['type'] = matches.group(1)
            values['id'] = matches.group(2)

        return values

    @classmethod
    def _find_player_url(cls, response):
        """
        Finds embedded player url in HTTP response.

        :param response: Response object.
        :returns: Player url (str).
        """
        url = ''
        matches = cls._player_re.search(response.text)
        if matches:
            tmp_url = matches.group(0).replace('&amp;', '&')
            if 'hash' not in tmp_url:
                # there's no hash in the URL, try to find it
                matches = cls._hash_re.search(response.text)
                if matches:
                    url = tmp_url + '&hash=' + matches.group(1)
            else:
                url = tmp_url

        return 'http://ceskatelevize.cz/' + url


class CeskatelevizeAPI2:
    _player_api = 'https://playlist.ceskatelevize.cz/'
    _url_re = re.compile(r'http(s)?://([^.]*.)?ceskatelevize.cz')
    _playlist_info_re = re.compile(r'{\s*"type":\s*"([a-z]+)",\s*"id":\s*"(\w+)"')
    _playlist_schema = validate.Schema({
        "CODE": validate.contains("OK"),
        "RESULT": {
            "playlist": [{
                "streamUrls": {
                    "main": validate.url(),
                }
            }]
        }
    })
    _ctcomp_re = re.compile(r'data-ctcomp="Video"\sdata-video-id="(?P<val1>[^"]*)"\sdata-ctcomp-data="(?P<val2>[^"]+)">')
    _ctcomp_schema = validate.Schema(
        validate.text,
        validate.transform(_ctcomp_re.findall),
        validate.transform(lambda vl: [{"video-id": v[0], "ctcomp-data": json.loads(html_unescape(v[1]))} for v in vl])
    )
    _playlist_info_schema = validate.Schema({
        "type": validate.text,
        "id": validate.any(validate.text, int),
        "key": validate.text,
        "date": validate.text,
        "requestSource": validate.text,
        "drm": int,
        validate.optional("canBePlay"): int,
        validate.optional("assetId"): validate.text,
        "quality": validate.text,
        validate.optional("region"): int
    })

    def __init__(self, session, url, res=None):
        self.session = session
        self.url = url
        self.response = res

    def _get_streams(self):
        if self.response is None:
            infos = self.session.http.get(self.url, schema=self._ctcomp_schema)
        else:
            infos = self.session.http.json(self.response, schema=self._ctcomp_schema)
        if not infos:
            # playlist infos not found
            raise PluginError('Cannot find playlist infos!')

        vod_prio = len(infos) == 2
        for info in infos:
            try:
                pl = info['ctcomp-data']['source']['playlist'][0]
            except KeyError:
                raise PluginError('Cannot find playlist info!')

            pl = self._playlist_info_schema.validate(pl)
            if vod_prio and pl['type'] != 'VOD':
                continue

            log.trace('{0!r}'.format(info))
            if pl['type'] == 'LIVE':
                data = {
                    "contentType": "live",
                    "items": [{
                        "id": pl["id"],
                        "assetId": pl["assetId"],
                        "key": pl["key"],
                        "playerType": "dash",
                        "date": pl["date"],
                        "requestSource": pl["requestSource"],
                        "drm": pl["drm"],
                        "quality": pl["quality"],
                    }]
                }
            elif pl['type'] == 'VOD':
                data = {
                    "contentType": "vod",
                    "items": [{
                        "id": pl["id"],
                        "key": pl["key"],
                        "playerType": "dash",
                        "date": pl["date"],
                        "requestSource": pl["requestSource"],
                        "drm": pl["drm"],
                        "canBePlay": pl["canBePlay"],
                        "quality": pl["quality"],
                        "region": pl["region"]
                    }]
                }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

        data = json.dumps(data)
        response = self.session.http.post(
            self._player_api,
            data="data={}".format(quote(data)),
            headers=headers
        )
        json_data = self.session.http.json(response, schema=self._playlist_schema)
        log.trace('{0!r}'.format(json_data))
        playlist = json_data['RESULT']['playlist'][0]['streamUrls']['main']
        yield from DASHStream.parse_manifest(self.session, playlist).items()


__plugin__ = Ceskatelevize
