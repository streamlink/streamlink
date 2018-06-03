import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, useragents
from streamlink.stream import DASHStream, HTTPStream
from streamlink.utils import parse_json


class Facebook(Plugin):
    _url_re = re.compile(r"https?://(?:www\.)?facebook\.com/[^/]+/videos")
    _mpd_re = re.compile(r'''(sd|hd)_src["']?\s*:\s*(?P<quote>["'])(?P<url>.+?)(?P=quote)''')
    _playlist_re = re.compile(r'''video:\[({url:".+?}\])''')
    _plurl_re = re.compile(r'''url:"(.*?)"''')

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    def _get_streams(self):
        res = http.get(self.url, headers={"User-Agent": useragents.CHROME})

        for match in self._mpd_re.finditer(res.text):
            manifest_url = match.group("url")
            if "\\/" in manifest_url:
                # if the URL is json encoded, decode it
                manifest_url = parse_json("\"{}\"".format(manifest_url))
            for s in DASHStream.parse_manifest(self.session, manifest_url).items():
                yield s
        else:
            match = self._playlist_re.search(res.text)
            playlist = match and match.group(1)
            if playlist:
                for url in {url.group(1) for url in self._plurl_re.finditer(playlist)}:
                    yield "live", HTTPStream(self.session, url)


__plugin__ = Facebook
