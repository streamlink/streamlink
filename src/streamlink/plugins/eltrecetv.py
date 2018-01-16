import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, useragents
from streamlink.stream import HLSStream
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
                                'User-Agent': useragents.ANDROID}
                res = http.get('https://api.iamat.com/metadata/atcodes/eltrece')
                yt_id = parse_json(res.text)["atcodes"][0]["context"]["ahora"]["vivo"]["youtubeVideo"]
                yt_url = "https://www.youtube.com/watch?v={0}".format(yt_id)
                return self.session.streams(yt_url)
            except BaseException:
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
                entry_id = parse_json(match.group(1).replace("&quot;", '"'))["entryId"]
                hls_url = "https://vodgc.com/p/111/sp/11100/playManifest/entryId/{0}/format/applehttp/protocol/https/a.m3u8".format(entry_id)
                return HLSStream.parse_variant_playlist(self.session, hls_url)
            except BaseException:
                self.logger.error("The requested VOD content is unavailable.")


__plugin__ = ElTreceTV
