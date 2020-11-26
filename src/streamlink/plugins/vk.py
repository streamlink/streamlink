import logging
import re
from html import unescape as html_unescape
from urllib.parse import unquote, urlparse

from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.plugin.api.utils import itertags
from streamlink.stream import HLSStream, HTTPStream
from streamlink.utils import update_scheme

log = logging.getLogger(__name__)


class VK(Plugin):

    API_URL = 'https://vk.com/al_video.php'

    _url_re = re.compile(r'''https?://(?:\w+\.)?vk\.com/video
        (?:\?z=video)?(?P<video_id>-?[0-9]*_[0-9]*)
        ''', re.VERBOSE)
    _url_catalog_re = re.compile(r"https?://(\w+\.)?vk\.com/videos-?[0-9]*")
    _vod_quality_re = re.compile(r"\.([0-9]*?)\.mp4")

    @classmethod
    def can_handle_url(cls, url):
        if cls._url_catalog_re.match(url) is not None:
            url = cls.follow_vk_redirect(url)
            if url is None:
                return False
        return cls._url_re.match(url) is not None

    @classmethod
    def follow_vk_redirect(cls, url):
        # If this is a 'videos' catalog URL
        # with an video ID in the GET request, get that instead
        parsed_url = urlparse(url)
        if parsed_url.path.startswith('/videos'):
            query = {v[0]: v[1] for v in [q.split('=') for q in parsed_url.query.split('&')] if v[0] == 'z'}
            try:
                true_path = unquote(query['z']).split('/')[0]
                return parsed_url.scheme + '://' + parsed_url.netloc + '/' + true_path
            except KeyError:
                # No redirect found in query string,
                # so return the catalog url and fail later
                return url
        else:
            return url

    def _get_streams(self):
        """
        Find the streams for vk.com
        :return:
        """
        self.session.http.headers.update({'User-Agent': useragents.IPHONE_6})

        # If this is a 'videos' catalog URL
        # with an video ID in the GET request, get that instead
        url = self.follow_vk_redirect(self.url)

        m = self._url_re.match(url)
        if not m:
            log.error('URL is not compatible: {0}'.format(url))
            return

        video_id = m.group('video_id')
        log.debug('video ID: {0}'.format(video_id))

        params = {
            'act': 'show_inline',
            'al': '1',
            'video': video_id,
        }
        res = self.session.http.post(self.API_URL, params=params)

        for _i in itertags(res.text, 'iframe'):
            if _i.attributes.get('src'):
                iframe_url = update_scheme(self.url, _i.attributes['src'])
                log.debug('Found iframe: {0}'.format(iframe_url))
                yield from self.session.streams(iframe_url).items()

        for _i in itertags(res.text.replace('\\', ''), 'source'):
            if _i.attributes.get('type') == 'application/vnd.apple.mpegurl':
                video_url = html_unescape(_i.attributes['src'])
                streams = HLSStream.parse_variant_playlist(self.session,
                                                           video_url)
                if not streams:
                    yield 'live', HLSStream(self.session, video_url)
                else:
                    yield from streams.items()
            elif _i.attributes.get('type') == 'video/mp4':
                q = 'vod'
                video_url = _i.attributes['src']
                m = self._vod_quality_re.search(video_url)
                if m:
                    q = '{0}p'.format(m.group(1))
                yield q, HTTPStream(self.session, video_url)


__plugin__ = VK
