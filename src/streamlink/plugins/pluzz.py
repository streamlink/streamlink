import logging
import re
import sys
import time

from streamlink.plugin import Plugin, PluginArgument, PluginArguments
from streamlink.plugin.api import validate
from streamlink.stream import DASHStream, HDSStream, HLSStream, HTTPStream
from streamlink.stream.ffmpegmux import MuxedStream

log = logging.getLogger(__name__)


class Pluzz(Plugin):
    GEO_URL = 'http://geo.francetv.fr/ws/edgescape.json'
    API_URL = 'http://sivideo.webservices.francetelevisions.fr/tools/getInfosOeuvre/v2/?idDiffusion={0}'
    TOKEN_URL = 'http://hdfauthftv-a.akamaihd.net/esi/TA?url={0}'
    SWF_PLAYER_URL = 'https://staticftv-a.akamaihd.net/player/bower_components/player_flash/dist/' \
                     'FranceTVNVPVFlashPlayer.akamai-7301b6035a43c4e29b7935c9c36771d2.swf'

    _url_re = re.compile(r'''
        https?://(
            (?:www\.)france\.tv/.+\.html |
            www\.(ludo|zouzous)\.fr/heros/[\w-]+ |
            (.+\.)?francetvinfo\.fr)
    ''', re.VERBOSE)
    _pluzz_video_id_re = re.compile(r'''(?P<q>["']*)videoId(?P=q):\s*["'](?P<video_id>[^"']+)["']''')
    _jeunesse_video_id_re = re.compile(r'playlist: \[{.*?,"identity":"(?P<video_id>.+?)@(?P<catalogue>Ludo|Zouzous)"')
    _sport_video_id_re = re.compile(r'data-video="(?P<video_id>.+?)"')
    _embed_video_id_re = re.compile(r'href="http://videos\.francetv\.fr/video/(?P<video_id>.+?)(?:@.+?)?"')
    _hds_pv_data_re = re.compile(r"~data=.+?!")
    _mp4_bitrate_re = re.compile(r'.*-(?P<bitrate>[0-9]+k)\.mp4')

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
                'format': validate.any(
                    None,
                    validate.text
                ),
                'url': validate.any(
                    None,
                    validate.url(),
                ),
                'statut': validate.text,
                'drm': bool,
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
        ),
        'subtitles': validate.any(
            [],
            validate.all(
                [{
                    'type': validate.text,
                    'url': validate.url(),
                    'format': validate.text
                }]
            )
        )
    })

    _player_schema = validate.Schema({'result': validate.url()})

    arguments = PluginArguments(
        PluginArgument("mux-subtitles", is_global=True)
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        # Retrieve geolocation data
        res = self.session.http.get(self.GEO_URL)
        geo = self.session.http.json(res, schema=self._geo_schema)
        country_code = geo['reponse']['geo_info']['country_code']
        log.debug('Country: {0}'.format(country_code))

        # Retrieve URL page and search for video ID
        res = self.session.http.get(self.url)
        if 'france.tv' in self.url:
            match = self._pluzz_video_id_re.search(res.text)
        elif 'ludo.fr' in self.url or 'zouzous.fr' in self.url:
            match = self._jeunesse_video_id_re.search(res.text)
        elif 'sport.francetvinfo.fr' in self.url:
            match = self._sport_video_id_re.search(res.text)
        else:
            match = self._embed_video_id_re.search(res.text)
        if match is None:
            return
        video_id = match.group('video_id')
        log.debug('Video ID: {0}'.format(video_id))

        res = self.session.http.get(self.API_URL.format(video_id))
        videos = self.session.http.json(res, schema=self._api_schema)
        now = time.time()

        offline = False
        geolocked = False
        drm = False
        expired = False

        streams = []
        for video in videos['videos']:
            log.trace('{0!r}'.format(video))
            video_url = video['url']

            # Check whether video format is available
            if video['statut'] != 'ONLINE':
                offline = offline or True
                continue

            # Check whether video format is geo-locked
            if video['geoblocage'] is not None and country_code not in video['geoblocage']:
                geolocked = geolocked or True
                continue

            # Check whether video is DRM-protected
            if video['drm']:
                drm = drm or True
                continue

            # Check whether video format is expired
            available = False
            for interval in video['plages_ouverture']:
                available = (interval['debut'] or 0) <= now <= (interval['fin'] or sys.maxsize)
                if available:
                    break
            if not available:
                expired = expired or True
                continue

            res = self.session.http.get(self.TOKEN_URL.format(video_url))
            video_url = res.text

            if '.mpd' in video_url:
                # Get redirect video URL
                res = self.session.http.get(res.text)
                video_url = res.url
                for bitrate, stream in DASHStream.parse_manifest(self.session,
                                                                 video_url).items():
                    streams.append((bitrate, stream))
            elif '.f4m' in video_url:
                for bitrate, stream in HDSStream.parse_manifest(self.session,
                                                                video_url,
                                                                is_akamai=True,
                                                                pvswf=self.SWF_PLAYER_URL).items():
                    # HDS videos with data in their manifest fragment token
                    # doesn't seem to be supported by HDSStream. Ignore such
                    # stream (but HDS stream having only the hdntl parameter in
                    # their manifest token will be provided)
                    pvtoken = stream.request_params['params'].get('pvtoken', '')
                    match = self._hds_pv_data_re.search(pvtoken)
                    if match is None:
                        streams.append((bitrate, stream))
            elif '.m3u8' in video_url:
                for stream in HLSStream.parse_variant_playlist(self.session, video_url).items():
                    streams.append(stream)
            # HBB TV streams are not provided anymore by France Televisions
            elif '.mp4' in video_url and '/hbbtv/' not in video_url:
                match = self._mp4_bitrate_re.match(video_url)
                if match is not None:
                    bitrate = match.group('bitrate')
                else:
                    # Fallback bitrate (seems all France Televisions MP4 videos
                    # seem have such bitrate)
                    bitrate = '1500k'
                streams.append((bitrate, HTTPStream(self.session, video_url)))

        if self.get_option("mux_subtitles") and videos['subtitles'] != []:
            substreams = {}
            for subtitle in videos['subtitles']:
                # TTML subtitles are available but not supported by FFmpeg
                if subtitle['format'] == 'ttml':
                    continue
                substreams[subtitle['type']] = HTTPStream(self.session, subtitle['url'])

            for quality, stream in streams:
                yield quality, MuxedStream(self.session, stream, subtitles=substreams)
        else:
            for stream in streams:
                yield stream

        if offline:
            log.error('Failed to access stream, may be due to offline content')
        if geolocked:
            log.error('Failed to access stream, may be due to geo-restricted content')
        if drm:
            log.error('Failed to access stream, may be due to DRM-protected content')
        if expired:
            log.error('Failed to access stream, may be due to expired content')


__plugin__ = Pluzz
