import re
import sys
import time

from streamlink.plugin import Plugin, PluginArguments, PluginArgument
from streamlink.plugin.api import http, validate
from streamlink.stream import DASHStream, HDSStream, HLSStream, HTTPStream
from streamlink.stream.ffmpegmux import MuxedStream
from streamlink.utils import update_scheme


class Pluzz(Plugin):
    GEO_URL = 'http://geo.francetv.fr/ws/edgescape.json'
    API_URL = 'http://sivideo.webservices.francetelevisions.fr/tools/getInfosOeuvre/v2/?idDiffusion={0}'
    PLAYER_GENERATOR_URL = 'https://sivideo.webservices.francetelevisions.fr/assets/staticmd5/getUrl?id=jquery.player.7.js'
    TOKEN_URL = 'http://hdfauthftv-a.akamaihd.net/esi/TA?url={0}'

    _url_re = re.compile(
        r'https?://((?:www)\.france\.tv/.+\.html|www\.(ludo|zouzous)\.fr/heros/[\w-]+|(sport|france3-regions)\.francetvinfo\.fr/.+?/(tv/direct)?)')
    _pluzz_video_id_re = re.compile(r'data-main-video="(?P<video_id>.+?)"')
    _jeunesse_video_id_re = re.compile(r'playlist: \[{.*?,"identity":"(?P<video_id>.+?)@(?P<catalogue>Ludo|Zouzous)"')
    _f3_regions_video_id_re = re.compile(r'"http://videos\.francetv\.fr/video/(?P<video_id>.+?)@Regions"')
    _sport_video_id_re = re.compile(r'data-video="(?P<video_id>.+?)"')
    _player_re = re.compile(
        r'src="(?P<player>//staticftv-a\.akamaihd\.net/player/jquery\.player.+?-[0-9a-f]+?\.js)"></script>')
    _swf_re = re.compile(
        r'"(bower_components/player_flash/dist/FranceTVNVPVFlashPlayer\.akamai-[0-9a-f]+\.swf)"')
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
        PluginArgument(
            "mux-subtitles",
            action="store_true",
            help="""
        Automatically mux available subtitles in to the output stream.
        """
        )
    )

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
        if 'france.tv' in self.url:
            match = self._pluzz_video_id_re.search(res.text)
        elif 'ludo.fr' in self.url or 'zouzous.fr' in self.url:
            match = self._jeunesse_video_id_re.search(res.text)
        elif 'france3-regions.francetvinfo.fr' in self.url:
            match = self._f3_regions_video_id_re.search(res.text)
        elif 'sport.francetvinfo.fr' in self.url:
            match = self._sport_video_id_re.search(res.text)
        if match is None:
            return
        video_id = match.group('video_id')

        # Retrieve SWF player URL
        swf_url = None
        res = http.get(self.PLAYER_GENERATOR_URL)
        player_url = update_scheme(self.url, http.json(res, schema=self._player_schema)['result'])
        res = http.get(player_url)
        match = self._swf_re.search(res.text)
        if match is not None:
            swf_url = 'https://staticftv-a.akamaihd.net/player/' + match.group(1)

        res = http.get(self.API_URL.format(video_id))
        videos = http.json(res, schema=self._api_schema)
        now = time.time()

        offline = False
        geolocked = False
        drm = False
        expired = False

        streams = []
        for video in videos['videos']:
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

            if ('.f4m' in video_url or
                '.mpd' in video_url or
                'france.tv' in self.url or
                'sport.francetvinfo.fr' in self.url):
                res = http.get(self.TOKEN_URL.format(video_url))
                video_url = res.text

            if '.mpd' in video_url:
                # Get redirect video URL
                res = http.get(res.text)
                video_url = res.url
                for bitrate, stream in DASHStream.parse_manifest(self.session,
                                                                 video_url).items():
                    streams.append((bitrate, stream))
            elif '.f4m' in video_url and swf_url is not None:
                for bitrate, stream in HDSStream.parse_manifest(self.session,
                                                                video_url,
                                                                is_akamai=True,
                                                                pvswf=swf_url).items():
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
            self.logger.error('Failed to access stream, may be due to offline content')
        if geolocked:
            self.logger.error('Failed to access stream, may be due to geo-restricted content')
        if drm:
            self.logger.error('Failed to access stream, may be due to DRM-protected content')
        if expired:
            self.logger.error('Failed to access stream, may be due to expired content')


__plugin__ = Pluzz
