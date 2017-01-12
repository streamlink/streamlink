import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream, HTTPStream


class Euronews(Plugin):
    _url_re = re.compile(r"http(?:s)?://(\w+)\.?euronews.com/(live|.*)")
    _re_vod = re.compile(r'<meta\s+property="og:video"\s+content="(http.*?)"\s*/>')
    _live_api_url = "http://fr.euronews.com/api/watchlive.json"
    _live_schema = validate.Schema({
        u"url": validate.url()
    })
    _stream_api_schema = validate.Schema({
        u'status': u'ok',
        u'primary': {
            validate.text: {
                validate.optional(u'hls'): validate.url(),
                validate.optional(u'rtsp'): validate.url(scheme="rtsp")
            }
        },
        validate.optional(u'backup'): {
            validate.text: {
                validate.optional(u'hls'): validate.url(),
                validate.optional(u'rtsp'): validate.url(scheme="rtsp")
            }
        }
    })

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    def _get_vod_stream(self):
        """
        Find the VOD video url
        :return: video url
        """
        res = http.get(self.url)
        video_urls = self._re_vod.findall(res.text)
        if len(video_urls):
            return dict(vod=HTTPStream(self.session, video_urls[0]))

    def _get_live_streams(self, language):
        """
        Get the live stream in a particular language
        :param language:
        :return:
        """
        res = http.get(self._live_api_url)
        live_res = http.json(res, schema=self._live_schema)
        api_res = http.get(live_res[u"url"])
        stream_data = http.json(api_res, schema=self._stream_api_schema)
        # find the stream in the requested language
        if language in stream_data[u'primary']:
            playlist_url = stream_data[u'primary'][language][u"hls"]
            return HLSStream.parse_variant_playlist(self.session, playlist_url)

    def _get_streams(self):
        """
        Find the streams for euronews
        :return:
        """
        match = self._url_re.match(self.url)
        language, path = match.groups()

        # remap domain to language (default to english)
        language = {"www": "en", "": "en", "arabic": "ar"}.get(language, language)

        if path == "live":
            return self._get_live_streams(language)
        else:
            return self._get_vod_stream()


__plugin__ = Euronews
