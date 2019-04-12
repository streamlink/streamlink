import re

from streamlink.plugin import Plugin
from streamlink.plugins.brightcove import BrightcovePlayer
from streamlink.stream import HLSStream


class BFMTV(Plugin):
    _url_re = re.compile(r'https://.+\.(?:bfmtv|01net)\.com')
    _brightcove_video_re = re.compile(r'data-holder="video(?P<video_id>[0-9]+)" data-account="(?P<account_id>[0-9]+)"')
    _brightcove_video_alt_re = re.compile(r'data-account="(?P<account_id>[0-9]+).*?data-video-id="(?P<video_id>[0-9]+)"', re.DOTALL)
    _embed_video_url_re = re.compile(r"\$YOPLAYER\('liveStitching', {.+?file: '(?P<video_url>[^\"]+?)'.+?}\);", re.DOTALL)

    @classmethod
    def can_handle_url(cls, url):
        return BFMTV._url_re.match(url)

    def _get_streams(self):
        # Retrieve URL page and search for Brightcove video data
        res = self.session.http.get(self.url)
        match = self._brightcove_video_re.search(res.text) or self._brightcove_video_alt_re.search(res.text)
        if match is not None:
            account_id = match.group('account_id')
            video_id = match.group('video_id')
            player = BrightcovePlayer(self.session, account_id)
            for stream in player.get_streams(video_id):
                yield stream
        else:
            # Try to get the stream URL in the page
            match = self._embed_video_url_re.search(res.text)
            if match is not None:
                video_url = match.group('video_url')
                if '.m3u8' in video_url:
                    for stream in HLSStream.parse_variant_playlist(self.session, video_url).items():
                        yield stream


__plugin__ = BFMTV
