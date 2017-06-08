import re

from streamlink.compat import urlparse
from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HLSStream, HTTPStream, RTMPStream
from streamlink.utils import parse_qsd


class DW(Plugin):
    _SMIL_API_URL = 'http://www.dw.com/smil/{}'
    _HTML5_API_URL = 'http://www.dw.com/html5Resource/{}'

    _url_re = re.compile(r'http://www\.dw\.com/')
    _stream_type_re = re.compile(r'<input type="hidden" name="player_type" value="(?P<stream_type>.+?)">')
    _stream_vod_data_re = re.compile(r'<input type="hidden" name="file_name" value="(?P<stream_url>.+?)">.*?'
                                     r'<input type="hidden" name="media_id" value="(?P<stream_id>\d+)">',
                                     re.DOTALL)
    _smil_schema = validate.Schema(
        validate.union({
            'base': validate.all(
                validate.xml_find('.//meta'),
                validate.xml_element(attrib={'base': validate.text}),
                validate.get('base')
            ),
            'streams': validate.all(
                validate.xml_findall('.//switch/*'),
                [
                    validate.all(
                        validate.getattr('attrib'),
                        {
                            'src': validate.text,
                            'system-bitrate': validate.all(
                                validate.text,
                                validate.transform(int),
                            ),
                            validate.optional('width'): validate.all(
                                validate.text,
                                validate.transform(int)
                            )
                        }
                    )
                ]
            )
        })
    )

    @classmethod
    def can_handle_url(cls, url):
        return DW._url_re.match(url)

    def _create_stream(self, url, quality=None):
        if url.startswith('rtmp://'):
            yield quality, RTMPStream(self.session, {'rtmp': url})
        elif url.endswith('.m3u8'):
            for stream in HLSStream.parse_variant_playlist(self.session, url).items():
                yield stream
        else:
            yield quality, HTTPStream(self.session, url)

    def _get_live_streams(self, page):
        # DW is available in different languages, depending on URL query parameter value
        query = parse_qsd(urlparse(self.url).query)
        channel_id = query.get('channel', '1')

        # All live streams are available on the web page, select the right one using the channel ID
        stream_re = re.compile(r'<div class="mediaItem" data-channel-id="{}".*?>.*?'
                               r'<input type="hidden" name="file_name" value="(?P<stream_url>.+?)">'.format(channel_id),
                               re.DOTALL)
        match = stream_re.search(page)
        if match is None:
            return

        stream_url = match.group('stream_url')
        for stream in self._create_stream(stream_url):
            yield stream

    def _get_vod_streams(self, stream_type, page):
        match = self._stream_vod_data_re.search(page)
        if match is None:
            return
        stream_url, stream_id = match.groups()

        if stream_type == 'video':
            stream_api_id = 'v-{}'.format(stream_id)
            default_quality = 'vod'
        elif stream_type == 'audio':
            stream_api_id = 'a-{}'.format(stream_id)
            default_quality = 'audio'
        else:
            return

        # Retrieve stream embed in web page
        for stream in self._create_stream(stream_url, default_quality):
            yield stream

        # Retrieve streams using API
        res = http.get(self._SMIL_API_URL.format(stream_api_id))
        videos = http.xml(res, schema=self._smil_schema)

        for video in videos['streams']:
            url = videos['base'] + video['src']
            if url == stream_url or url.replace('_dwdownload.', '.') == stream_url:
                continue

            if video['system-bitrate'] > 0:
                # If width is available, use it to select the best stream amongst those with same bitrate
                quality = '{}k'.format((video['system-bitrate'] + video.get('width', 0))//1000)
            else:
                quality = default_quality
            for stream in self._create_stream(url, quality):
                yield stream

    def _get_streams(self):
        res = http.get(self.url)
        match = self._stream_type_re.search(res.text)
        if match is None:
            return

        stream_type = match.group('stream_type')
        if stream_type == 'dwlivestream':
            streams = self._get_live_streams(res.text)
        else:
            streams = self._get_vod_streams(stream_type, res.text)

        for stream in streams:
            yield stream

__plugin__ = DW
