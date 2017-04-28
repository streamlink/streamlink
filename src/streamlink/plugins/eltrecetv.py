import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, useragents, validate
from streamlink.stream import HLSStream, HTTPStream
from streamlink.utils import parse_json

class ElTreceTV(Plugin):
    _url_re = re.compile(r'https?://(?:www\.)?eltrecetv.com.ar/.+')

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    def _get_streams(self):

        video_url_found_hls = ""

        if "eltrecetv.com.ar/vivo" in self.url.lower():
            http.headers = {'Referer': self.url,
            'User-Agent': "ArtearPlayer/3.2.42 (Linux;Android 4.4.2) ExoPlayerLib/1.5.9"}
            video_url_found_hls = "http://stream.eltrecetv.com.ar/live13/13tv/13tv1/playlist.m3u8"
        else:
            http.headers = {'Referer': self.url,
            'User-Agent': useragents.CHROME}
            res = http.get(self.url)
            _player_re = re.compile(r'''data-kaltura="([^"]+)"''')
            match = _player_re.search(res.text)
            if not match:
                return
            json_video_search = parse_json(match.group(1).replace("&quot;", '"'))
            video_url_found_hls = "https://vodgc.com/p/111/sp/11100/playManifest/entryId/" + json_video_search["entryId"] + "/format/applehttp/protocol/https/a.m3u8"

        if video_url_found_hls:
            hls_streams = HLSStream.parse_variant_playlist(self.session, video_url_found_hls)
            for s in hls_streams.items():
                yield s

__plugin__ = ElTreceTV
