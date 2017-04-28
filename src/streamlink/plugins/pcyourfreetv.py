import re

from streamlink.compat import parse_qsl, unquote
from streamlink.plugin import Plugin, PluginOptions
from streamlink.plugin.api import http
from streamlink.stream import HLSStream


class PCYourFreeTV(Plugin):
    LIVE_TV_URL = 'http://pc-yourfreetv.com/indexlivetv.php?page_id=1'

    _login_url = 'http://pc-yourfreetv.com/home.php'
    _url_re = re.compile(r'http://pc-yourfreetv\.com/indexplayer\.php\?channel=.+?&page_id=\d+')
    _token_re = re.compile(r'\bsrc="indexplayer\.php\?channel=.+?&(?P<tokens>.+?)"')
    _player_re = re.compile(r"<script language=JavaScript>m='(?P<player>.+?)'", re.DOTALL)
    _video_url_re = re.compile(r"jwplayer\('.+?'\)\.setup\({.+?file: \"(?P<video_url>[^\"]+?)\".+?}\);", re.DOTALL)

    options = PluginOptions({
        'username': None,
        'password': None
    })

    @classmethod
    def can_handle_url(cls, url):
        return PCYourFreeTV._url_re.match(url)

    def login(self, username, password):
        res = http.post(
            self._login_url,
            data={
                'user_name': username,
                'user_pass': password,
                'login': 'Login'
            }
        )

        return username in res.text

    def _get_streams(self):
        username = self.get_option('username')
        password = self.get_option('password')

        if username is None or password is None:
            self.logger.error("PC-YourFreeTV requires authentication, use --pcyourfreetv-username "
                              "and --pcyourfreetv-password to set your username/password combination")
            return

        if self.login(username, password):
            self.logger.info("Successfully logged in as {0}", username)

        # Get a fresh authorization token
        res = http.get(self.LIVE_TV_URL)
        match = self._token_re.search(res.text)
        if match is None:
            return

        # Retrieve URL page and search for stream data
        res = http.get(self.url, params=parse_qsl(match.group('tokens')))
        match = self._player_re.search(res.text)
        if match is None:
            return

        while match is not None:
            player = unquote(match.group('player'))
            match = self._player_re.search(player)

        match = self._video_url_re.search(player)
        if match is None:
            return

        video_url = match.group('video_url')
        if '.m3u8' in video_url:
            streams = HLSStream.parse_variant_playlist(self.session, video_url)
            if len(streams) != 0:
                for stream in streams.items():
                    yield stream
            else:
                # Not a HLS playlist
                yield 'live', HLSStream(self.session, video_url)


__plugin__ = PCYourFreeTV
