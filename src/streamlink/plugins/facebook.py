import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, useragents
from streamlink.stream import DASHStream


class Facebook(Plugin):
    _url_re = re.compile(r"https?://(?:www\.)?facebook\.com/[^/]+/videos/(?P<video_id>\d+)")
    _mpd_re = re.compile(r'''hd_src["']?\s*:\s*(?P<quote>["'])(?P<url>.*?)(?P=quote)''')

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    def _get_streams(self):
        res = http.get(self.url, headers={"User-Agent": useragents.CHROME})
        with open("temp.html", "w") as f:
            f.write(res.text)

        match = self._mpd_re.search(res.text)

        manifest_url = match and match.group("url")

        if manifest_url:
            return DASHStream.parse_manifest(self.session, manifest_url)



__plugin__ = Facebook
