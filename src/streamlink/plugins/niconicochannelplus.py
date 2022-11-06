"""
$description NicoNico Channel Plus (nicochannel+) is a new feature of Niconico Channel.
$url nicochannel.jp
$type vod
$account Not required. Full-length videos are accessible.
$notes Downloading non-free content is not recommended.
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(
        r'^https?://nicochannel\.jp/(?P<channel>[a-z0-9_-]+)/video/(?P<id>sm[a-zA-Z0-9]+)$'
    )
)
class NicoNicoChannelPlus(Plugin):
    _URL_API_VIDEO_PAGE_INFO = 'https://nfc-api.nicochannel.jp/fc/video_pages/{video_id}'
    _URL_API_SESSION_ID = 'https://nfc-api.nicochannel.jp/fc/video_pages/{video_id}/session_ids'
    _URL_API_MASTER_PLAYLIST = 'https://hls-auth.cloud.stream.co.jp/auth/index.m3u8?session_id={session_id}'

    def get_video_page_info(self, video_id: str) -> dict:
        return self.session.http.get(
            self._URL_API_VIDEO_PAGE_INFO.format(video_id=video_id),
            schema=validate.Schema(
                validate.parse_json(),
                {'data': {'video_page': {'title': str}}},
                validate.get(('data', 'video_page')),
            ),
        )

    def get_master_playlist_url(self, video_id: str) -> str:
        session_id = self.session.http.post(
            self._URL_API_SESSION_ID.format(video_id=video_id),
            json={},
            schema=validate.Schema(
                validate.parse_json(),
                {'data': {'session_id': str}},
                validate.get(('data', 'session_id')),
            ),
        )

        return self._URL_API_MASTER_PLAYLIST.format(session_id=session_id)

    def _get_streams(self):
        self.id = self.match.group('id')
        self.author = self.match.group('channel')

        video_info = self.get_video_page_info(self.id)
        playlist_url = self.get_master_playlist_url(self.id)

        self.title = video_info['title']

        log.info(f'ID:      {self.id}')
        log.info(f'Channel: {self.author}')
        log.info(f'Title:   {self.title}')

        return HLSStream.parse_variant_playlist(self.session, playlist_url)


__plugin__ = NicoNicoChannelPlus
