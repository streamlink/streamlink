
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents, validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json, update_scheme


class IDF1(Plugin):
    DACAST_API_URL = 'https://json.dacast.com/b/{}/{}/{}'
    DACAST_TOKEN_URL = 'https://services.dacast.com/token/i/b/{}/{}/{}'

    _url_re = re.compile(r'https?://www\.idf1\.fr/(videos/[^/]+/[^/]+\.html|live\b)')
    _video_id_re = re.compile(r"""
            dacast\('(?P<broadcaster_id>\d+)_(?P<video_type>[a-z]+)_(?P<video_id>\d+)',\s*'replay_content',\s*data\);
        """, re.VERBOSE)
    _video_id_alt_re = re.compile(r'''
            <script\s+
                src="https://player.dacast.com/js/player.js"\s+
                id="(?P<broadcaster_id>\d+)_(?P<video_type>[cf])_(?P<video_id>\d+)"
        ''', re.VERBOSE)
    _player_url = 'http://ssl.p.jwpcdn.com/player/v/7.12.6/jwplayer.flash.swf'

    _api_schema = validate.Schema(
        validate.transform(parse_json),
        {
            validate.optional('html5'): validate.all(
                [
                    {
                        'src': validate.url()
                    },
                ],
            ),
            'hls': validate.url(),
            'hds': validate.url()
        },
        validate.transform(
            lambda x: [update_scheme(IDF1.DACAST_API_URL, x['hls']), x['hds']] + [y['src'] for y in x.get('html5', [])]
        )
    )

    _token_schema = validate.Schema(
        validate.transform(parse_json),
        {'token': validate.text},
        validate.get('token')
    )

    _user_agent = useragents.IE_11

    @classmethod
    def can_handle_url(cls, url):
        return IDF1._url_re.match(url)

    def _get_streams(self):
        res = self.session.http.get(self.url)
        match = self._video_id_re.search(res.text) or self._video_id_alt_re.search(res.text)
        if match is None:
            return
        broadcaster_id = match.group('broadcaster_id')
        video_type = match.group('video_type')
        video_id = match.group('video_id')

        videos = self.session.http.get(
            self.DACAST_API_URL.format(broadcaster_id, video_type, video_id),
            schema=self._api_schema
        )
        token = self.session.http.get(
            self.DACAST_TOKEN_URL.format(broadcaster_id, video_type, video_id),
            schema=self._token_schema,
            headers={'referer': self.url}
        )
        parsed = []

        for video_url in videos:
            video_url += token

            # Ignore duplicate video URLs
            if video_url in parsed:
                continue
            parsed.append(video_url)

            # Ignore HDS streams (broken)
            if '.m3u8' in video_url:
                yield from HLSStream.parse_variant_playlist(self.session, video_url).items()


__plugin__ = IDF1
