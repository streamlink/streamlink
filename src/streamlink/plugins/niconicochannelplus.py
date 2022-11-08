"""
$description NicoNico Channel Plus (nicochannel+) is a new feature of Niconico Channel.
$url nicochannel.jp
$type live, vod
"""

import logging
import re

from streamlink.exceptions import PluginError
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(
        r'^https?://nicochannel\.jp/(?P<channel>[a-z0-9_-]+)/(?:video|live)/(?P<id>sm[a-zA-Z0-9]+)$'
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
                {'data': {'video_page': {
                    'title': str,
                    'type': str,
                    'live_started_at': validate.any(str, None),
                    'live_finished_at': validate.any(str, None),
                }}},
                validate.get(('data', 'video_page')),
            ),
        )

    def get_master_playlist_url(self, video_id: str, video_info: dict) -> str:
        video_type = video_info['type']

        if video_type == 'vod':
            payload: dict = {}
        elif video_type == 'live':
            if not video_info['live_started_at']:
                raise PluginError('Live is not started yet.')

            if not video_info['live_finished_at']:
                # Live is available.
                payload = {}
            else:
                # Live is already ended, try DVR.
                payload = {'broadcast_type': 'dvr'}
        else:
            raise PluginError(f'Unknown video type: {video_type}')

        session_id = self.session.http.post(
            self._URL_API_SESSION_ID.format(video_id=video_id),
            json=payload,
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
        playlist_url = self.get_master_playlist_url(self.id, video_info)

        self.title = video_info['title']

        return HLSStream.parse_variant_playlist(self.session, playlist_url)


__plugin__ = NicoNicoChannelPlus
