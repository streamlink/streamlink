import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream, HTTPStream


class OlympicChannel(Plugin):
    _url_re = re.compile(r"http(?:s)?://(\w+)\.?olympicchannel.com/../(?P<type>tv|playback)/(livestream-.\d|.*)/")
    _live_api_url = "https://www.olympicchannel.com{0}api/v2/metadata/{1}"
    _stream_get_url = "https://www.olympicchannel.com/en/proxy/viewings/"
    _stream_api_schema = validate.Schema({
        u'status': u'ok',
        u'primary': validate.url(),
        validate.optional(u'backup'): validate.url()
    })

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    def _get_vod_streams(self):
        page = http.get(self.url)
        asset = re.search(r'asse_.{32}', str(page._content)).group(0)
        post_data = '{"asset_url":"/api/assets/%s/"}' % asset
        stream_data = http.json(http.post(self._stream_get_url, data=post_data))['objects'][0]['level3']['streaming_url']
        return HLSStream.parse_variant_playlist(self.session, stream_data)

    def _get_live_streams(self, lang, path):
        """
        Get the live stream in a particular language
        :param lang:
        :param path:
        :return:
        """
        res = http.get(self._live_api_url.format(lang, path))
        live_res = http.json(res)['default']['uid']
        post_data = '{"channel_url":"/api/channels/%s/"}' % live_res
        try:
            stream_data = http.json(http.post(self._stream_get_url, data=post_data))['stream_url']
        except BaseException:
            stream_data = http.json(http.post(self._stream_get_url, data=post_data))['channel_url']
        return HLSStream.parse_variant_playlist(self.session, stream_data)

    def _get_streams(self):
        """
        Find the streams for OlympicChannel
        :return:
        """
        match = self._url_re.match(self.url)
        type_of_stream = match.group('type')
        lang = re.search(r"/../", self.url).group(0)

        if type_of_stream == 'tv':
            path = re.search(r"tv/.*-\d/$", self.url).group(0)

            return self._get_live_streams(lang, path)
        elif type_of_stream == 'playback':
            path = re.search(r"/playback/.*/$", self.url).group(0)
            return self._get_vod_streams()


__plugin__ = OlympicChannel
