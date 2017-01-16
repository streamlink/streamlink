import re

from streamlink.exceptions import PluginError
from streamlink.plugin import Plugin
from streamlink.plugin.api import http, useragents, validate
from streamlink.stream import HDSStream, HLSStream, HTTPStream


class CanalPlus(Plugin):
    API_URL = 'http://service.canal-plus.com/video/rest/getVideos/{0}/{1}?format=json'
    CHANNEL_MAP = {'canalplus': 'cplus', 'c8': 'd8', 'cstar': 'd17'}
    HDCORE_VERSION = '3.1.0'
    # Secret parameter needed to download HTTP videos on canalplus.fr
    SECRET = 'pqzerjlsmdkjfoiuerhsdlfknaes'

    _url_re = re.compile(r'''
        http://
        (
            www\.(?P<channel>canalplus|c8|cstar)\.fr/.*pid.+?\.html(\?(?P<video_id>[0-9]+))? |
            replay\.(?P<replay_channel>c8|cstar)\.fr/video/(?P<replay_video_id>[0-9]+)
        )
''', re.VERBOSE)
    _video_id_re = re.compile(r'\bdata-video="(?P<video_id>[0-9]+)"')
    _mp4_bitrate_re = re.compile(r'.*_(?P<bitrate>[0-9]+k)\.mp4')
    _api_schema = validate.Schema({
        'MEDIA': validate.Schema({
            'VIDEOS': validate.Schema({
                validate.text: validate.any(
                    validate.url(),
                    ''
                )
            })
        })
    })
    _user_agent = useragents.CHROME


    @classmethod
    def can_handle_url(cls, url):
        return CanalPlus._url_re.match(url)


    def _get_streams(self):
        # Get video ID and channel from URL
        match = self._url_re.match(self.url)
        channel = match.group('channel')
        if channel is None:
            # Replay website
            channel = match.group('replay_channel')
            video_id = match.group('replay_video_id')
        else:
            video_id = match.group('video_id')
            if video_id is None:
                # Retrieve URL page and search for video ID
                res = http.get(self.url)
                match = self._video_id_re.search(res.text)
                if match is None:
                    return
                video_id = match.group('video_id')

        res = http.get(self.API_URL.format(self.CHANNEL_MAP[channel], video_id))
        videos = http.json(res, schema=self._api_schema)
        parsed = []
        headers = {'User-Agent': self._user_agent}
        for quality, video_url in list(videos['MEDIA']['VIDEOS'].items()):
            # Ignore empty URLs
            if video_url == '':
                continue

            # Ignore duplicate video URLs
            if video_url in parsed:
                continue
            parsed.append(video_url)

            try:
                if '.f4m' in video_url:
                    for stream in HDSStream.parse_manifest(self.session,
                                                           video_url,
                                                           params={'hdcore': self.HDCORE_VERSION},
                                                           headers=headers).items():
                        yield stream
                elif '.m3u8' in video_url:
                    for stream in HLSStream.parse_variant_playlist(self.session,
                                                                   video_url,
                                                                   headers=headers).items():
                        yield stream
                elif '.mp4' in video_url:
                    # Get bitrate from video filename
                    match = self._mp4_bitrate_re.match(video_url)
                    if match is not None:
                        bitrate = match.group('bitrate')
                    else:
                        bitrate = quality
                    yield bitrate, HTTPStream(self.session,
                                              video_url,
                                              params={'secret': self.SECRET},
                                              headers=headers)
            except PluginError:
                self.logger.error('Failed to access stream, may be due to geo-restriction')
                raise


__plugin__ = CanalPlus
