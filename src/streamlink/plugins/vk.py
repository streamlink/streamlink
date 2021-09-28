import logging
import re
from html import unescape as html_unescape
from urllib.parse import parse_qsl, unquote, urlparse

from streamlink.exceptions import NoStreamsError
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import useragents
from streamlink.plugin.api.utils import itertags
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream
from streamlink.utils.url import update_scheme

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:\w+\.)?vk\.com/video(?:\?z=video)?(?P<video_id>-?\d*_\d*)"
))
@pluginmatcher(re.compile(
    r"https?://(\w+\.)?vk\.com/videos-?\d*"
))
class VK(Plugin):
    API_URL = 'https://vk.com/al_video.php'

    _vod_quality_re = re.compile(r"\.([0-9]*?)\.mp4")

    def follow_vk_redirect(self):
        # If this is a 'videos' catalog URL
        # with an video ID in the GET request, get that instead
        if self.matches[1]:
            try:
                parsed_url = urlparse(self.url)
                true_path = next(unquote(v).split('/')[0] for k, v in parse_qsl(parsed_url.query) if k == "z")
                self.url = parsed_url.scheme + '://' + parsed_url.netloc + '/' + true_path
            except StopIteration:
                raise NoStreamsError(self.url)

    def _get_streams(self):
        self.session.http.headers.update({'User-Agent': useragents.IPHONE_6})

        self.follow_vk_redirect()

        video_id = self.match.group('video_id')
        log.debug('video ID: {0}'.format(video_id))

        params = {
            'act': 'show_inline',
            'al': '1',
            'video': video_id,
        }
        res = self.session.http.post(self.API_URL, params=params)

        for _i in itertags(res.text, 'iframe'):
            if _i.attributes.get('src'):
                iframe_url = update_scheme("https://", _i.attributes["src"])
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
