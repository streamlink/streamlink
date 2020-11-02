import json
import logging
import re

from streamlink.plugin import Plugin, PluginError
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class Vlive(Plugin):
    _url_re = re.compile(r"https?://(?:www.)vlive\.tv/(?P<format>video|post)/(?P<id>[0-9\-]+)")
    _page_info = re.compile(r'window\.__PRELOADED_STATE__\s*=\s*({.*})\s*<', re.DOTALL)
    _playinfo_url = "https://www.vlive.tv/globalv-web/vam-web/old/v3/live/%s/playInfo"

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        video_page = self.session.http.get(self.url, headers=dict(referer=self.url))
        if video_page.status_code != 200:
            raise PluginError('Could not get video page (HTTP Status {})'
                              .format(video_page.status_code))

        page_info_js = self._page_info.search(video_page.text)
        if not page_info_js:
            raise PluginError('Could not find page info')

        page_info = json.loads(page_info_js.group(1))
        if not page_info['postDetail'].get('post'):
            raise PluginError('Could not find video info')

        video_json = page_info['postDetail']['post']['officialVideo']

        video_type = video_json['type']
        if video_type == 'VOD':
            raise PluginError('VODs are not supported')

        url_format, video_id = re.match(self._url_re, self.url).group('format', 'id')
        if url_format == 'post':
            video_id = str(video_json['videoSeq'])

        video_status = video_json['status']
        if video_status == 'ENDED':
            raise PluginError('Stream has ended')
        elif video_status != 'ON_AIR':
            raise PluginError('Unknown video status: %s' % video_status)

        stream_info_js = self.session.http.get(self._playinfo_url % video_id,
                                               headers=dict(referer=self.url))
        if stream_info_js.status_code != 200:
            raise PluginError('Could not get stream info (HTTP Status {})'
                              .format(stream_info_js.status_code))

        stream_info = json.loads(stream_info_js.text)

        streams = dict()
        # All "resolutions" have a variant playlist with only one entry, so just combine them
        for i in stream_info['result']['streamList']:
            res_streams = HLSStream.parse_variant_playlist(self.session, i['serviceUrl'])
            if len(res_streams.values()) > 1:
                log.warning('More than one stream in variant playlist, using first entry!')

            streams[i['streamName']] = res_streams.popitem()[1]

        return streams


__plugin__ = Vlive
