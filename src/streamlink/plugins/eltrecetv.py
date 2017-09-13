import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, useragents
from streamlink.utils import parse_json

class ElTreceTV(Plugin):
    _url_re = re.compile(r'https?://(?:www\.)?eltrecetv.com.ar/.+')

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    def _get_streams(self):
        if "eltrecetv.com.ar/vivo" in self.url.lower():
            try:
                http.headers = {'Referer': self.url,
                'User-Agent': "ArtearPlayer/3.2.42 (Linux;Android 4.4.2) ExoPlayerLib/1.5.9"}
                res = http.get('https://api.iamat.com/metadata/atcodes/eltrece')
                live_search = res.text
                live_search = live_search[live_search.index('"vivo":{"provider":"youtube","youtubeVideo":')+45 :]
                live_search = live_search[: live_search.index('"')]
                LIVE_URL_FOUND = 'https://www.youtube.com/watch?v=' + live_search
                return self.session.streams(LIVE_URL_FOUND)
            except:
                self.logger.info("Live content is temporarily unavailable. Please try again later.")
        else:
            try:
                http.headers = {'Referer': self.url,
                'User-Agent': useragents.CHROME}
                res = http.get(self.url)
                _player_re = re.compile(r'''data-kaltura="([^"]+)"''')
                match = _player_re.search(res.text)
                if not match:
                    return
                json_video_search = parse_json(match.group(1).replace("&quot;", '"'))
                VOD_URL_FOUND = "https://vodgc.com/p/111/sp/11100/playManifest/entryId/" + json_video_search["entryId"] + "/format/applehttp/protocol/https/a.m3u8"
                return self.session.streams(VOD_URL_FOUND)
            except:
                self.logger.error("The requested VOD content is unavailable.")

__plugin__ = ElTreceTV
