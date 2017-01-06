import os.path
import re
import sys
import time

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HDSStream, HLSStream


class Pluzz(Plugin):
    GEO_URL = 'http://geo.francetv.fr/ws/edgescape.json'
    API_URL = 'http://sivideo.webservices.francetelevisions.fr/tools/getInfosOeuvre/v2/?idDiffusion={0}&catalogue=Pluzz'
    HDS_TOKEN_URL = 'http://hdfauthftv-a.akamaihd.net/esi/TA?url={0}'

    _url_re = re.compile(r'http://pluzz\.francetv\.fr/(videos/.+\.html|[\w-]+)')
    _video_id_re = re.compile(r'id="current_video" href="http://.+?\.(?:francetv|francetelevisions)\.fr/(?:video/|\?id-video=)(?P<video_id>.+?)"')
    _player_re = re.compile(r'<script type="text/javascript" src="(?P<player>//staticftv-a\.akamaihd\.net/player/jquery\.player.+?-[0-9a-f]+?\.js)"></script>')
    _swf_re = re.compile(r'getUrl\("(?P<swf>/bower_components/player_flash/dist/FranceTVNVPVFlashPlayer\.akamai.+?\.swf)"\)')
    _hds_pv_data_re = re.compile(r"~data=.+?!")

    _geo_schema = validate.Schema({
        'reponse': {
            'geo_info': {
                'country_code': validate.text
            }
        }
    })

    _api_schema = validate.Schema({
        'videos': validate.all(
            [{
                'format': validate.text,
                'url': validate.any(
                    None,
                    validate.url(),
                ),
                'statut': validate.text,
                'geoblocage': validate.any(
                    None,
                    [validate.all(validate.text)]
                ),
                'plages_ouverture': validate.all(
                    [{
                        'debut': validate.any(
                            None,
                            int
                        ),
                        'fin': validate.any(
                            None,
                            int
                        )
                    }]
                )
            }]
        )
    })


    @classmethod
    def can_handle_url(cls, url):
        return Pluzz._url_re.match(url)


    def _get_streams(self):
        # Retrieve geolocation data
        res = http.get(self.GEO_URL)
        geo = http.json(res, schema=self._geo_schema)
        country_code = geo['reponse']['geo_info']['country_code']

        # Retrieve URL page and search for video ID
        res = http.get(self.url)
        match = self._video_id_re.search(res.text)
        if match is None:
            return
        video_id = match.group('video_id')

        # Retrieve SWF player URL
        match = self._player_re.search(res.text)
        swf_url = None
        if match is not None:
            player_url = 'http:' + match.group('player')
            res = http.get(player_url)
            match = self._swf_re.search(res.text)
            if match is not None:
                swf_url = os.path.dirname(player_url) + match.group('swf')

        res = http.get(self.API_URL.format(video_id))
        videos = http.json(res, schema=self._api_schema)
        now = time.time()

        for video in videos['videos']:
            # Check whether video format is available
            if video['statut'] != 'ONLINE':
                continue

            # Check whether video format is geo-locked
            if video['geoblocage'] is not None and country_code not in video['geoblocage']:
                continue

            # Check whether video format is expired
            available = False
            for interval in video['plages_ouverture']:
                available = (interval['debut'] or 0) <= now <= (interval['fin'] or sys.maxsize)
                if available:
                    break
            if not available:
                continue

            video_url = video['url']
            # TODO: add DASH streams once supported
            if '.f4m' in video_url and swf_url is not None:
                res = http.get(self.HDS_TOKEN_URL.format(video_url))
                video_url = res.text
                for bitrate, stream in HDSStream.parse_manifest(self.session, video_url, pvswf=swf_url).items():
                    # HDS videos with data in their manifest fragment token
                    # doesn't seem to be supported by HDSStream. Ignore such
                    # stream (but HDS stream having only the hdntl parameter in
                    # their manifest token will be provided)
                    pvtoken = stream.request_params['params'].get('pvtoken', '')
                    match = self._hds_pv_data_re.search(pvtoken)
                    if match is None:
                        yield bitrate, stream
            elif '.m3u8' in video_url:
                for stream in HLSStream.parse_variant_playlist(self.session, video_url).items():
                    yield stream


__plugin__ = Pluzz
