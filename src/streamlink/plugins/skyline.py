import logging
import re
from urllib.parse import urljoin, urlparse

from streamlink.TaskTimer import TaskTimer
from streamlink.exceptions import (
    NoPluginError,
)
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.stream import HLSStream

SKYLINE_VERSION = '2022-06-02'

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r'https?://www\.skylinewebcams\.com/(?P<url>.+)'))
class Skyline(Plugin):
    # playlists
    _playlist_re = re.compile(r'''(?sx)
        (?:["']|=|&quot;)(?P<url>
            (?<!title=["'])
            (?<!["']title["']:["'])
                [^"'<>\s\;{}]+\.(?:m3u8)
            (?:\?[^"'<>\s\\{}]+)?)/?
        (?:\\?["']|(?<!;)\s|>|\\&quot;)
    ''')

    def __init__(self, url):
        super(Skyline, self).__init__(url)
        self.timer = None
        self.referer = self.url
        self.session.http.headers.update({'Referer': self.referer})

        # START - how often _get_streams already run
        self._run = len(self.url)
        # END

    def repair_url(self, url, base_url, stream_base=''):
        new_url = url.replace('\\', '').replace('livee.', 'live.')
        new_url = urljoin(base_url, new_url)
        return new_url

    def _make_url_list(self, old_list, base_url):
        new_list = []
        for url in old_list:
            new_url = self.repair_url(url, base_url)
            new_list += [new_url]

        return new_list

    def _resolve_playlist(self, playlist_all):
        playlist_referer = 'https://www.skylinewebcams.com/'
        self.session.http.headers.update({'Referer': playlist_referer})

        for url in playlist_all:
            parsed_url = urlparse(url)

            if (parsed_url.path.endswith(('.m3u8'))
                or parsed_url.query.endswith(('.m3u8'))):
                try:
                    streams = HLSStream.parse_variant_playlist(self.session, url).items()
                    if not streams:
                        yield 'live', HLSStream(self.session, url)
                    for s in streams:
                        yield s
                    log.debug('HLS URL - {0}'.format(url))
                except Exception as e:
                    log.error('Skip HLS with error {0}'.format(str(e)))
            else:
                log.error('parsed URL - {0}'.format(url))

    def _res_text(self, url):
        res = self.session.http.get(url, allow_redirects=True)
        return res.text

    def _get_streams(self):
        if self._run <= 1:
            log.info('Version {0}'.format(SKYLINE_VERSION))

        log.info('  {0}. URL={1}'.format(self._run, self.url))

        # GET website content
        self.html_text = self._res_text(self.url)

        # Playlist URL
        playlist_all = self._playlist_re.findall(self.html_text)
        if playlist_all:
            log.debug('Found Playlists: {0}'.format(len(playlist_all)))
            playlist_list = self._make_url_list(playlist_all,
                                                "https://hd-auth.skylinewebcams.com/"
                                                )
            if playlist_list:
                log.info('Found Playlists: {0} (valid)'.format(
                    len(playlist_list)))
                return self._resolve_playlist(playlist_list)
        else:
            log.trace('No Playlists')

        raise NoPluginError

    def stream_opening(self):
        self.timer = TaskTimer()
        # 把任务加入任务队列
        self.timer.join_task(self._res_text, [self.url], interval=30)  # 每10秒执行1次
        # 开始执行（此时才会创建线程）
        self.timer.start()

    def stream_closing(self):
        self.timer.stop()


__plugin__ = Skyline
