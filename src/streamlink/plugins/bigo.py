import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents, validate
from streamlink.stream import HLSStream


class Bigo(Plugin):
    _url_re = re.compile(r"https?://(?:www\.)?bigo\.tv/([^/]+)$")
    _api_url = "https://bigo.tv/studio/getInternalStudioInfo"

    _video_info_schema = validate.Schema({
        "code": 0,
        "msg": "success",
        "data": {
            "hls_src": validate.any(None, "", validate.url())
        }
    })

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        match = self._url_re.match(self.url)
        res = self.session.http.post(
            self._api_url,
            allow_redirects=True,
            headers={"User-Agent": useragents.IPHONE_6},
            data={'siteId': match.group(1)}
        )
        data = self.session.http.json(res, schema=self._video_info_schema)
        videourl = data["data"]["hls_src"]
        if videourl:
            yield "live", HLSStream(self.session, videourl)


__plugin__ = Bigo
