"""
$description NicoNico Channel Plus (ニコニコチャンネルプラス, nicochannel+) is a new feature of Niconico Channel.
$url nicochannel.jp
$type vod
$account Not required. Full-length videos are accessible.
$notes Downloading non-free content is not recommended.
"""

import json
import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import HTTPSession
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(
        r'^https?://nicochannel\.jp/(?P<channel>[a-z0-9_-]+)/video/(?P<id>sm[a-zA-Z0-9]+)$'
    )
)
class NicoNicoChannelPlus(Plugin):
    def get_video_page_info(self, http: HTTPSession, video_id: str) -> dict:
        video_page_json = json.loads(
            http.get(
                url=f'https://nfc-api.nicochannel.jp/fc/video_pages/{video_id}',
            ).content
        )['data']['video_page']

        return video_page_json

    def get_master_playlist_url(self, http: HTTPSession, video_id: str) -> str:
        session_id = json.loads(
            http.post(
                url=f'https://nfc-api.nicochannel.jp/fc/video_pages/{video_id}/session_ids',
                data=str({}).encode('ascii'),
                headers={
                    'content-type': 'application/json',
                }
            ).content
        )['data']['session_id']

        return f'https://hls-auth.cloud.stream.co.jp/auth/index.m3u8?session_id={session_id}'

    def _get_streams(self):
        self.id = self.match.group('id')
        self.author = self.match.group('channel')

        video_info = self.get_video_page_info(self.session.http, self.id)
        playlist_url = self.get_master_playlist_url(self.session.http, self.id)

        self.title = video_info['title']

        log.info(f'ID:      {self.id}')
        log.info(f'Channel: {self.author}')
        log.info(f'Title:   {self.title}')

        for name, stream in HLSStream.parse_variant_playlist(
            self.session, playlist_url
        ).items():
            yield name, stream


__plugin__ = NicoNicoChannelPlus
