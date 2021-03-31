import logging
import re
from urllib.parse import urljoin

from streamlink.plugin import Plugin
from streamlink.plugins.brightcove import BrightcovePlayer

log = logging.getLogger(__name__)


class BFMTV(Plugin):
    _url_re = re.compile(r'https://.+\.(?:bfmtv|01net)\.com')
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
        r'i\?\(N="[^"]+",y="(?P<video_id>[0-9]+).*"data-account"\s*:\s*"(?P<account_id>[0-9]+)',
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        # Retrieve URL page and search for Brightcove video data
        res = self.session.http.get(self.url)
        match = self._brightcove_video_re.search(res.text) or self._brightcove_video_alt_re.search(res.text)
        if match:
            account_id = match.group('account_id')
            log.debug(f'Account ID: {account_id}')
            video_id = match.group('video_id')
            log.debug(f'Video ID: {video_id}')
            player = BrightcovePlayer(self.session, account_id)
            yield from player.get_streams(video_id)

        # Try to find the Dailymotion video ID
        match = self._embed_video_id_re.search(res.text)
        if match:
            video_id = match.group('video_id')
            log.debug(f'Video ID: {video_id}')
            yield from self.session.streams(self._dailymotion_url.format(video_id)).items()

        # Try the JS for Brightcove video data
        match = self._main_js_url_re.search(res.text)
        if match:
            log.debug(f'JS URL: {urljoin(self.url, match.group(1))}')
            res = self.session.http.get(urljoin(self.url, match.group(1)))
            match = self._js_brightcove_video_re.search(res.text)
            if match:
                account_id = match.group('account_id')
                log.debug(f'Account ID: {account_id}')
                video_id = match.group('video_id')
                log.debug(f'Video ID: {video_id}')
                player = BrightcovePlayer(self.session, account_id)
                yield from player.get_streams(video_id)


__plugin__ = BFMTV
