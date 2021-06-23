import logging
import re
from urllib.parse import urljoin, urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api.utils import itertags
from streamlink.plugins.brightcove import BrightcovePlayer
from streamlink.stream import HTTPStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r'https?://(?:[\w-]+\.)+(?:bfmtv|01net)\.com'
))
class BFMTV(Plugin):
    _dailymotion_url = 'https://www.dailymotion.com/embed/video/{}'
    _brightcove_video_re = re.compile(
        r'accountid="(?P<account_id>[0-9]+).*?videoid="(?P<video_id>[0-9]+)"',
        re.DOTALL
    )
    _brightcove_video_alt_re = re.compile(
        r'data-account="(?P<account_id>[0-9]+).*?data-video-id="(?P<video_id>[0-9]+)"',
        re.DOTALL
    )
    _embed_video_id_re = re.compile(
        r'<iframe.*?src=".*?/(?P<video_id>\w+)"',
        re.DOTALL
    )
    _main_js_url_re = re.compile(r'src="([\w/]+/main\.\w+\.js)"')
    _js_brightcove_video_re = re.compile(
        r'i\?\([A-Z]="[^"]+",y="(?P<video_id>[0-9]+).*"data-account"\s*:\s*"(?P<account_id>[0-9]+)',
    )

    def _get_streams(self):
        res = self.session.http.get(self.url)

        m = self._brightcove_video_re.search(res.text) or self._brightcove_video_alt_re.search(res.text)
        if m:
            account_id = m.group('account_id')
            log.debug(f'Account ID: {account_id}')
            video_id = m.group('video_id')
            log.debug(f'Video ID: {video_id}')
            player = BrightcovePlayer(self.session, account_id)
            yield from player.get_streams(video_id)
            return

        # Try to find the Dailymotion video ID
        m = self._embed_video_id_re.search(res.text)
        if m:
            video_id = m.group('video_id')
            log.debug(f'Video ID: {video_id}')
            yield from self.session.streams(self._dailymotion_url.format(video_id)).items()
            return

        # Try the JS for Brightcove video data
        m = self._main_js_url_re.search(res.text)
        if m:
            log.debug(f'JS URL: {urljoin(self.url, m.group(1))}')
            res = self.session.http.get(urljoin(self.url, m.group(1)))
            m = self._js_brightcove_video_re.search(res.text)
            if m:
                account_id = m.group('account_id')
                log.debug(f'Account ID: {account_id}')
                video_id = m.group('video_id')
                log.debug(f'Video ID: {video_id}')
                player = BrightcovePlayer(self.session, account_id)
                yield from player.get_streams(video_id)
                return

        # Audio Live
        audio_url = None
        for source in itertags(res.text, 'source'):
            url = source.attributes.get('src')
            if url:
                p_url = urlparse(url)
                if p_url.path.endswith(('.mp3')):
                    audio_url = url

        # Audio VOD
        for div in itertags(res.text, 'div'):
            if div.attributes.get('class') == 'audio-player':
                audio_url = div.attributes.get('data-media-url')

        if audio_url:
            yield 'audio', HTTPStream(self.session, audio_url)
            return


__plugin__ = BFMTV
