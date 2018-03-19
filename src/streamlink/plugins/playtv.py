import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HDSStream, HLSStream


class PlayTV(Plugin):
    FORMATS_URL = 'http://playtv.fr/player/initialize/{0}/'
    API_URL = 'http://playtv.fr/player/play/{0}/?format={1}&language={2}&bitrate={3}'

    _url_re = re.compile(r'http://(?:playtv\.fr/television|play\.tv/live-tv/\d+)/(?P<channel>[^/]+)/?')

    _formats_schema = validate.Schema({
        'streams': validate.any(
            [],
            {
                validate.text: validate.Schema({
                    validate.text: {
                        'bitrates': validate.all([
                            validate.Schema({
                                'value': int
                            })
                        ])
                    }
                })
            }
        )
    })
    _api_schema = validate.Schema({
        'url': validate.url()
    })

    @classmethod
    def can_handle_url(cls, url):
        return PlayTV._url_re.match(url)

    def _get_streams(self):
        match = self._url_re.match(self.url)
        channel = match.group('channel')

        res = http.get(self.FORMATS_URL.format(channel))
        streams = http.json(res, schema=self._formats_schema)['streams']
        if streams == []:
            self.logger.error('Channel may be geo-restricted, not directly provided by PlayTV or not freely available')
            return

        for language in streams:
            for protocol, bitrates in list(streams[language].items()):
                # - Ignore non-supported protocols (RTSP, DASH)
                # - Ignore deprecated Flash (RTMPE/HDS) streams (PlayTV doesn't provide anymore a Flash player)
                if protocol in ['rtsp', 'flash', 'dash', 'hds']:
                    continue

                for bitrate in bitrates['bitrates']:
                    if bitrate['value'] == 0:
                        continue
                    api_url = self.API_URL.format(channel, protocol, language, bitrate['value'])
                    res = http.get(api_url)
                    video_url = http.json(res, schema=self._api_schema)['url']
                    bs = '{0}k'.format(bitrate['value'])

                    if protocol == 'hls':
                        for _, stream in HLSStream.parse_variant_playlist(self.session, video_url).items():
                            yield bs, stream
                    elif protocol == 'hds':
                        for _, stream in HDSStream.parse_manifest(self.session, video_url).items():
                            yield bs, stream


__plugin__ = PlayTV
